#!/usr/bin/env python3
"""Compute a cold-start status view without changing source artifacts.

Exit codes: 0 report produced, 2 usage or unreadable workspace.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json
import re
from datetime import date, datetime, timezone

from kitlib import fsio, graph, hashing, ids, rtm, schema, tables, workspace  # noqa: E402

UNKNOWN = "unknown"


def age_days(value, today):
    try:
        return max(0, (today - date.fromisoformat(str(value)[:10])).days)
    except ValueError:
        return UNKNOWN


def report_cell(base, filename, key):
    path = base / "_meta" / filename
    if not path.exists():
        return UNKNOWN
    text = path.read_text(encoding="utf-8")
    doc = tables.parse(text)
    if filename == "lint-report.md" and doc.table and "Severity" in doc.table.header:
        gate = re.search(r"Gate:\s*([a-z-]+)", text)
        if not gate:
            return UNKNOWN
        blocking = []
        for row in doc.table.rows:
            subject = row[doc.table.col("Subject")] if "Subject" in doc.table.header else ""
            location = row[doc.table.col("Location")] if "Location" in doc.table.header else ""
            applies = (
                subject in (key, key.split(":", 1)[1], "", "—") or key.split(":", 1)[1] in location
            )
            waived = doc.table.get(row[0], "Waiver") if "Waiver" in doc.table.header else None
            if applies and row[doc.table.col("Severity")] == "error" and waived in (None, "", "—"):
                blocking.append(row[0])
        return gate.group(1) + (": fail " + ", ".join(blocking) if blocking else ": pass")
    if doc.table:
        matches = [
            row
            for row in doc.table.rows
            if any(str(ref) in (key, key.split(":", 1)[1]) for ref in ids.find_refs(row[0]))
        ]
        if matches:
            return " | ".join(matches[0][1:])
    lines = [
        line.strip()
        for line in text.splitlines()
        if any(str(ref) in (key, key.split(":", 1)[1]) for ref in ids.find_refs(line))
    ]
    return "; ".join(lines) if lines else UNKNOWN


def signoff_state(entity):
    approvals = entity.fm.get("signoffs") or []
    if not approvals:
        return UNKNOWN
    digest = hashing.draft_hash(entity.path.read_text(encoding="utf-8"))
    states = []
    for approval in approvals:
        text = json.dumps(approval) if isinstance(approval, dict) else str(approval)
        hashes = re.findall(r"sha256:([0-9a-f]{12,64})", text)
        if "stale" in text.lower():
            states.append("stale")
        elif hashes:
            states.append("fresh" if all(digest[7:].startswith(h) for h in hashes) else "stale")
        else:
            states.append(UNKNOWN)
    return (
        "stale" if "stale" in states else "fresh" if all(s == "fresh" for s in states) else UNKNOWN
    )


def recommend(state, lint, drift, signoff, questions, changes):
    if drift not in (UNKNOWN, "none", "—", "clean"):
        return "review", "BA then PO"
    if changes:
        return "sw-review", "PO"
    if state == "draft":
        return "sw-spec", "BA"
    if questions and state == "in-review":
        return "sw-review", "PO"
    if signoff == "stale":
        return "sw-review", "PO"
    if state in ("withdrawn", "superseded"):
        return "trace capability", "BA"
    if state == "ready-for-dev":
        return "implementation", "Dev and QA"
    if state == "ready-to-publish":
        return ("sw-publish", "BA (after PO OK)") if signoff == "fresh" else ("sw-review", "PO")
    if state == "in-review":
        return "sw-review", "PO"
    if state == "published":
        return "review", "BA"
    if state == "draft":
        return (
            ("sw-spec", "BA") if re.search(r"fail|error", lint, re.I) else ("lint capability", "BA")
        )
    return UNKNOWN, UNKNOWN


def build_report(root: Path, scopes=None, today=None):
    today = today or datetime.now(timezone.utc).date()
    entities, findings = rtm.scan(root)
    result = []
    for scope in scopes or workspace.list_scopes(root):
        base = workspace.scope_dir(root, scope)
        registry = rtm.read_table(
            base / "_meta/id-registry.md", list(schema.REGISTRY_COLUMNS)
        ).table
        matrix = rtm.read_table(base / "_meta/rtm.md", rtm.rtm_header()).table
        for key, entity in sorted(entities.items()):
            if not key.startswith(scope + ":") or entity.kind != "feature":
                continue
            state = str(entity.fm.get("status") or UNKNOWN)
            lint = report_cell(base, "lint-report.md", key)
            drift = matrix.get(key, "Drift [sw-publish]")
            if drift in (None, "", "—"):
                drift = report_cell(base, "drift-report.md", key)
            related = {key} | {e.key for e in entities.values() if e.parent == key}
            linked = [e for e in entities.values() if related & e.refs]
            questions = sorted(
                e.key
                for e in entities.values()
                if e.kind == "q"
                and e.fm.get("status") in schema.OPEN_Q
                and related & graph.declared_affects(e.fm, scope)
            )
            changes = sorted(
                e.key
                for e in linked
                if e.kind == "cr" and e.fm.get("status") in ("proposed", "in-review", "approved")
            )
            signoff = signoff_state(entity)
            idle = age_days(entity.fm.get("updated"), today)
            snapshot = registry.get(key, "Last snapshot")
            snapshot_age = UNKNOWN
            if snapshot and snapshot != "—":
                candidate = (base / snapshot).resolve()
                if not candidate.is_relative_to(base.resolve()):
                    raise ValueError("snapshot path escapes project")
                if candidate.is_file():
                    from kitlib import frontmatter

                    fm = frontmatter.parse(candidate.read_text(encoding="utf-8")).fm or {}
                    snapshot_age = age_days(fm.get("fetched_at", fm.get("updated")), today)
            from kitlib import lifecycle

            board_item = lifecycle.feature(base, key)
            next_skill, turn = recommend(state, lint, drift, signoff, questions, changes)
            if (
                state in ("draft", "ready-to-publish", "published", "ready-for-dev")
                and not changes
                and drift in (UNKNOWN, "none", "—", "clean")
            ):
                next_skill = (
                    "sw-" + board_item["station"]
                    if board_item["condition"] != "unknown"
                    else "status capability"
                )
            result.append(
                {
                    "id": key,
                    "state": state,
                    "station": board_item["station"],
                    "condition": board_item["condition"],
                    "blockers": board_item["blockers"],
                    "lint": lint,
                    "jira": registry.get(key, "Jira key") or UNKNOWN,
                    "drift": drift,
                    "open_questions": questions,
                    "open_changes": changes,
                    "signoff": signoff,
                    "snapshot_age_days": snapshot_age,
                    "idle_days": idle,
                    "idle": idle >= 14 if isinstance(idle, int) else UNKNOWN,
                    "next": next_skill,
                    "turn": turn,
                }
            )
    result.sort(key=lambda item: (item["state"] != "ready-for-dev", item["id"]))
    return {"features": result, "findings": findings}


def render(report):
    lines = ["# Feature status", ""]
    for item in report["features"]:
        records = [f"{key.split(':')[-1]} open" for key in item["open_questions"]]
        records += [f"{key.split(':')[-1]} open" for key in item["open_changes"]]
        lines.append(
            f"{item['id']} | {item['state']} | lint {item['lint']} | Jira: "
            f"{item['jira']} | "
            + (", ".join(records) or "open records: none")
            + f" | next: {item['next']} ({item['turn']})"
            + f" | drift: {item['drift']} | sign-off: {item['signoff']}"
            + f" | snapshot age: {item['snapshot_age_days']} days | idle: "
            f"{item['idle_days']} days" + (" (14+ days)" if item["idle"] is True else "")
        )
    lines.extend(report["findings"])
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--save",
        action="store_true",
        help="write only _meta/status.md; requires an unambiguous scope",
    )
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run the sw-start workspace setup first")
        if (
            args.scope
            or args.save
            or workspace.mode_of(root) == "flat"
            or "projects" in cwd.relative_to(root).parts
        ):
            scopes = [workspace.resolve(root, args.scope, cwd=cwd, write=args.save)]
        else:
            scopes = workspace.list_scopes(root)
        report = build_report(root, scopes)
        if args.save:
            fsio.atomic_write(
                workspace.scope_dir(root, scopes[0]) / "_meta/status.md", render(report)
            )
        print(
            json.dumps(report, indent=2) if args.json else render(report),
            end="\n" if args.json else "",
        )
        return 0
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
