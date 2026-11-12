"""Durable, local lifecycle decisions and a rebuildable per-item board.

Decision records never grant approval or remote permission. A lock and pending
journal make incomplete multi-file writes visible instead of reporting success.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from kitlib import frontmatter, fsio, hashing, ids, tables, workspace, writelog

VERSION = 1
ACTIONS = {
    "submit-review",
    "return-spec",
    "return-review",
    "reopen-shape",
    "accept-slice",
    "request-publish",
    "defer-publish",
    "set-destination",
}
INVALIDATES = {"return-spec", "return-review", "reopen-shape"}


def decisions(base: Path, key: str) -> list[dict]:
    """Read only locally executed lifecycle records; reject forks and broken chains."""
    records = []
    for path in sorted((base / "records").glob("DEC-*.md")):
        if path.is_symlink():
            raise ValueError("symlink decision record")
        parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
        fm = parsed.fm or {}
        if fm.get("subtype") != "lifecycle" or fm.get("target") != key:
            continue
        if (
            parsed.error
            or fm.get("schema_version") != VERSION
            or fm.get("action") not in ACTIONS
            or fm.get("origin") != "local-transition"
            or fm.get("status") != "accepted"
            or fm.get("id") != ids.id_from_name(path.name)
        ):
            raise ValueError(f"invalid lifecycle decision: {path.name}")
        records.append(fm)
    by_id = {r["id"]: r for r in records}
    chain = []
    previous = ""
    while len(chain) < len(records):
        following = [r for r in records if r.get("predecessor", "") == previous]
        if len(following) != 1:
            raise ValueError(f"conflicting lifecycle history for {key}")
        current = following[0]
        if current["id"] in {r["id"] for r in chain}:
            raise ValueError("cyclic lifecycle history")
        chain.append(current)
        previous = current["id"]
    if len(by_id) != len(chain):
        raise ValueError("duplicate lifecycle identity")
    return chain


def approval_state(base: Path, feat: str, text: str) -> str:
    fm = frontmatter.parse(text).fm or {}
    signoffs = fm.get("signoffs") or []
    if not signoffs:
        return "unknown"
    scope = str(workspace.load(base / "project.yaml")["scope"])
    try:
        history = decisions(base, f"{scope}:{feat}")
    except ValueError:
        return "invalidated"
    invalidation = next((r for r in reversed(history) if r["action"] in INVALIDATES), None)
    if invalidation:
        if fm.get("approval_after") != invalidation["id"]:
            return "invalidated"
        old = set(invalidation.get("signoffs") or [])
        signoffs = [s for s in signoffs if s not in old]
    if (base / "_meta/lifecycle-pending.json").exists():
        return "invalidated"
    digest = hashing.short(hashing.draft_hash(text))
    return "fresh" if any(digest in str(s) and "https://" in str(s) for s in signoffs) else "stale"


def _registry(base: Path):
    return tables.parse((base / "_meta/id-registry.md").read_text(encoding="utf-8")).table


def publication(base: Path, key: str) -> dict:
    registry = _registry(base)
    state = registry.get(key, "State") if registry else None
    jira = registry.get(key, "Jira key") if registry else None
    digest = registry.get(key, "Last published draft hash") if registry else None
    return {
        "published": state == "published" and bool(digest and digest != "—"),
        "jira": jira if jira and jira != "—" else None,
        "hash": digest,
    }


def feature(base: Path, key: str, status: str = "reserved") -> dict:
    feat = key.split(":")[-1]
    path = base / "02-drafts" / f"{feat}.story.md"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    parsed = frontmatter.parse(text)
    fm = parsed.fm or {}
    status = str(fm.get("status", status))
    result = {
        "id": key,
        "status": status,
        "station": "spec",
        "condition": "not-started",
        "blockers": [],
        "available": [],
        "approval": "unknown",
        "publication": publication(base, key),
        "planning": {"passing": False},
    }
    if status in ("withdrawn", "superseded"):
        result.update(station="inactive", condition="complete")
        return result
    try:
        history = decisions(base, key)
        if (base / "_meta/lifecycle-pending.json").exists():
            raise ValueError("incomplete lifecycle transaction; inspect lifecycle-pending.json")
        if text and (parsed.error or not parsed.fm):
            raise ValueError("invalid story front matter")
        result["approval"] = approval_state(base, feat, text) if text else "unknown"
        latest = next((r for r in reversed(history) if r["action"] != "set-destination"), {})
        action = latest.get("action")
        destination = next(
            (r["destination"] for r in reversed(history) if r.get("destination")), None
        )
        result["destination"] = destination or workspace.output_default(base, key.split(":")[0])
        if action == "reopen-shape":
            result.update(station="shape", condition="in-progress", available=["accept-slice"])
        elif not text:
            result["available"] = ["sw-spec"]
        elif status == "draft":
            result.update(condition="in-progress", available=["sw-spec", "submit-review"])
        elif status == "in-review" or result["approval"] in ("stale", "invalidated"):
            result.update(station="review", condition="in-progress", available=["sw-review"])
        elif status in ("ready-to-publish", "published", "ready-for-dev"):
            from kitlib import task_validation

            planning = task_validation.planning(base, feat)
            result["planning"] = planning
            result.update(
                station="plan",
                condition="complete" if planning["passing"] else "blocked",
                blockers=planning["findings"],
                available=["sw-plan"],
            )
            if planning["passing"] and not result["publication"]["published"]:
                result["available"].append("request-publish")
                if action == "request-publish":
                    result.update(
                        station="publish", condition="in-progress", available=["sw-publish"]
                    )
        else:
            raise ValueError(f"unknown feature status: {status}")
        if status in ("published", "ready-for-dev") and not result["publication"]["published"]:
            result["blockers"].append("published status lacks registry publication evidence")
            result["condition"] = "blocked"
    except (ValueError, OSError, KeyError) as exc:
        result.update(condition="unknown", blockers=[str(exc)], available=[])
    return result


def input_hash(base: Path) -> str:
    """Bind confirmation to current artifacts, decisions and mappings, not a cache."""
    paths = []
    for folder in ("01-analysis", "02-drafts", "03-plan", "records", "snapshots"):
        paths.extend(p for p in (base / folder).rglob("*.md") if not p.is_symlink())
    paths += [base / "project.yaml", base / "_meta/id-registry.md", base / "_meta/lint-report.md"]
    payload = [
        (str(p.relative_to(base)), hashing.bytes_hash(p.read_bytes()))
        for p in sorted(set(paths))
        if p.is_file()
    ]
    return hashing.text_hash(json.dumps(payload, sort_keys=True))


def transition(
    base: Path, key: str, action: str, *, confirm: str | None = None, destination: str | None = None
) -> dict:
    """Preview unless the exact current token is supplied. No remote operations."""
    scope = str(workspace.load(base / "project.yaml")["scope"])
    if not key.startswith(scope + ":") or not ids.matches_type("feature", key.split(":")[-1]):
        raise ValueError("transition requires a qualified feature in the resolved scope")
    if action not in ACTIONS:
        raise ValueError("unsupported lifecycle action")
    if destination is not None and destination not in ("markdown", "jira", "both"):
        raise ValueError("invalid destination")
    log = base / "_meta/write-log.md"
    unfinished = writelog.unfinished(log)
    failed = [
        e for e in writelog.read(log) if e.kind == "RESULT" and e.fields and e.fields[0] == "error"
    ]
    if action in ("defer-publish", "return-spec", "return-review", "reopen-shape") and (
        unfinished or failed
    ):
        raise ValueError("remote write uncertainty requires recovery before local rollback")
    current = feature(base, key)
    if current["condition"] == "unknown" or current["station"] == "inactive":
        raise ValueError("cannot transition unknown or inactive feature")
    if action == "request-publish" and "request-publish" not in current["available"]:
        raise ValueError("publication requires a current passing plan and active approval")
    if action == "defer-publish" and current["station"] != "publish":
        raise ValueError("feature is not awaiting publication")
    allowed_from = {
        "return-spec": {"review", "plan", "publish"},
        "reopen-shape": {"spec"},
    }
    if action in allowed_from and current["station"] not in allowed_from[action]:
        raise ValueError("transition does not target an earlier station")
    if action == "submit-review" and current["station"] != "spec":
        raise ValueError("only a draft in spec can be submitted")
    if action == "accept-slice" and current["station"] != "shape":
        raise ValueError("feature slice is not reopened")
    if action == "return-review" and current["station"] != "plan":
        raise ValueError("return-review requires an approved feature in plan")
    if (
        action in ("return-spec", "return-review", "reopen-shape")
        and current["publication"]["published"]
    ):
        raise ValueError(
            "published requirements require the baseline and change-request amendment path"
        )
    if action == "set-destination" and destination is None:
        raise ValueError("set-destination requires a destination")
    feat = key.split(":")[-1]
    story = base / "02-drafts" / f"{feat}.story.md"
    for protected in (base / "records", base / "_meta", story):
        if protected.is_symlink() or not protected.resolve().is_relative_to(base.resolve()):
            raise ValueError("transition paths must remain inside the scope and not be symlinks")
    if not story.is_file():
        raise ValueError("create the reserved feature story before transitioning")
    if action == "submit-review":
        report = base / "_meta/lint-report.md"
        if not report.is_file() or "0 blocking error(s)" not in report.read_text(encoding="utf-8"):
            raise ValueError("a passing lint gate is required before submission")
    history = decisions(base, key)
    fingerprint = input_hash(base)
    payload = {"target": key, "action": action, "destination": destination, "inputs": fingerprint}
    digest = hashing.short(hashing.text_hash(json.dumps(payload, sort_keys=True)))
    token = f"TRANSITION {key} {action} {digest}"
    result = {**payload, "confirm": token, "applied": False}
    if confirm is None:
        return result
    if confirm != token:
        raise ValueError("confirmation does not match the current transition")
    lock = base / "_meta/lifecycle.lock"
    with lock.open("x", encoding="utf-8"):
        try:
            if input_hash(base) != fingerprint:
                raise ValueError("workspace changed; regenerate transition preview")
            pending = base / "_meta/lifecycle-pending.json"
            if pending.exists():
                raise ValueError("an incomplete lifecycle transaction needs recovery")
            text = story.read_text(encoding="utf-8")
            fm, body = frontmatter.split(text)
            identity = ids.next_id("DEC", ids.taken_ids(base))
            record = {
                "id": identity,
                "type": "dec",
                "title": f"{key} {action}",
                "aliases": [],
                "subtype": "lifecycle",
                "status": "accepted",
                "schema_version": VERSION,
                "origin": "local-transition",
                "scope": scope,
                "target": key,
                "affects": [key],
                "action": action,
                "predecessor": history[-1]["id"] if history else "",
                "expected_inputs": fingerprint,
                "confirmation": token,
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "signoffs": list(fm.get("signoffs") or []),
            }
            if destination:
                record["destination"] = destination
            statuses = {
                "submit-review": "in-review",
                "return-review": "in-review",
                "return-spec": "draft",
                "reopen-shape": "draft",
                "accept-slice": "draft",
            }
            if action in statuses:
                fm["status"] = statuses[action]
            updated = frontmatter.render(fm, body)
            fsio.atomic_write(pending, json.dumps({**result, "record": identity}) + "\n")
            fsio.atomic_write(story, updated)
            target = base / "records" / ids.record_filename(identity, record["title"])
            with target.open("x", encoding="utf-8") as handle:
                handle.write(frontmatter.render(record, f"# {key}: {action}\n"))
            pending.unlink()
            return {**result, "applied": True, "record": identity}
        finally:
            lock.unlink()
