"""Prepare and execute one explicitly confirmed Jira story change."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from kitlib import (
    adf,
    frontmatter,
    hashing,
    jira_diff,
    jira_port,
    miniyaml,
    tables,
    workspace,
)
from pathlib import Path

CONFIRM = re.compile(r"^PUBLISH ([A-Z]{2,5}:FEAT-\d{3}) ([0-9a-f]{8})$")
PROPERTY = "specwright.identity"


class PublishError(ValueError):
    """A precondition failed; no external write is allowed."""


@dataclass
class Context:
    root: Path
    base: Path
    scope: str
    scope_id: str
    draft: Path
    card: Path
    registry: Path
    rtm: Path
    log: Path
    manifest: dict
    jira_key: str | None = None


def context(root: Path, feat: str, scope: str | None = None) -> Context:
    base_root = workspace.find_root(root) or root
    selected = workspace.resolve(base_root, scope, None, root, write=True)
    base = workspace.scope_dir(base_root, selected)
    manifest = miniyaml.loads((base / "project.yaml").read_text(encoding="utf-8"))
    scope_id = f"{selected}:{feat}"
    draft = base / "02-drafts" / f"{feat}.story.md"
    return Context(
        base_root,
        base,
        selected,
        scope_id,
        draft,
        base / "02-drafts" / f"{feat}.card.md",
        base / "_meta/id-registry.md",
        base / "_meta/rtm.md",
        base / "_meta/write-log.md",
        manifest,
    )


def preconditions(ctx: Context, lint_report: str = "") -> list[str]:
    errors = []
    draft = ctx.draft.read_text(encoding="utf-8")
    fm, _ = frontmatter.split(draft)
    if fm.get("status") != "ready-to-publish":
        errors.append("draft is not ready-to-publish")
    signoffs = fm.get("signoffs") or []
    if not any(
            "https://" in str(x) and hashing.short(hashing.draft_hash(draft)) in str(x)
            for x in signoffs
    ):
        errors.append("signoff is absent, stale or unverifiable")
    report = ctx.base / "_meta/lint-report.md"
    if lint_report:
        if "0 blocking error(s)" not in lint_report:
            errors.append("publish lint gate is not clean")
    elif not report.is_file() or "0 blocking error(s)" not in report.read_text():
        errors.append("publish lint report is absent or not clean")
    if ctx.manifest.get("publish", {}).get("transitions") is True:
        errors.append("workflow transitions must stay off")
    return errors


def registry_key(ctx: Context) -> str | None:
    table = tables.parse(ctx.registry.read_text(encoding="utf-8")).table
    value = table.get(ctx.scope_id, "Jira key") if table else None
    return None if value in (None, tables.EMPTY) else value


def identity(ctx: Context, port: jira_port.Port, project: str, feat: str) -> str:
    """Registry wins; labels and properties only identify candidates to verify."""
    known = registry_key(ctx)
    if known:
        return known
    candidates = port.search_by_label(project, f"feat:{feat}")
    if len(candidates) > 1:
        raise PublishError(f"duplicate identity candidates: {[c.get('key') for c in candidates]}")
    if not candidates:
        return "NEW"
    key = str(candidates[0].get("key"))
    value = port.get_property(key, PROPERTY)
    if isinstance(value, dict) and value.get("id") not in (None, ctx.scope_id):
        raise PublishError("entity property identifies another feature")
    return key


def payload(ctx: Context, fields: dict) -> dict:
    """Convert only owned fields; foreign labels and workflow data stay untouched."""
    draft = ctx.draft.read_text(encoding="utf-8")
    fm, body = frontmatter.split(draft)
    owned = dict(fields)
    owned["description"] = adf.md_to_adf(body)
    owned["summary"] = str(fm.get("jira_summary"))
    labels = set(owned.get("labels") or [])
    labels |= {"specwright", f"feat:{fm['id']}", f"proj:{ctx.scope}"}
    owned["labels"] = sorted(labels)
    return owned


def operations(
        ctx: Context, action: str, fields: dict, key: str, updated: str
) -> list[jira_port.Operation]:
    """Include dependent property writes in the same hash-bound plan."""
    if action == "no-op":
        return []
    result = []
    if action == "create":
        result.append(
            jira_port.Operation(
                "create", {"fields": fields}, idempotency_note="ambiguous create is never retried"
            )
        )
        result.append(
            jira_port.Operation(
                "set_property",
                {
                    "key": "$created",
                    "property_key": PROPERTY,
                    "value": {
                        "id": ctx.scope_id,
                        "draft": hashing.draft_hash(ctx.draft.read_text()),
                    },
                },
                idempotency_note="runs only after the create result supplies its key",
            )
        )
    else:
        result.append(
            jira_port.Operation(
                "edit",
                {"key": key, "fields": fields},
                expect_updated=updated,
                idempotency_note="rechecks updated before edit",
            )
        )
    return result


def substitute(operation: jira_port.Operation, created_key: str) -> jira_port.Operation:
    """Resolve the one advertised dependent path; never mutate the confirmed plan."""
    data = json.loads(json.dumps(operation.payload))
    if data.get("key") == "$created":
        data["key"] = created_key
    return jira_port.Operation(
        operation.kind, data, operation.expect_updated, operation.idempotency_note
    )


def confirmed(token: str, result: dict) -> bool:
    match = CONFIRM.match(token.strip())
    return bool(
        match and match.group(1) == result["scope_id"] and match.group(2) == result["short_hash"]
    )


def execute(
        ctx: Context, port: jira_port.Port, plan: jira_port.Plan, run: str
) -> jira_port.Outcome:
    """Bind every dependent operation to the original confirmed plan hash."""
    original = [asdict(operation) for operation in plan.operations]
    completed, results, created_key = 0, [], None
    for operation in plan.operations:
        if asdict(operation) not in original:
            raise PublishError("operation is not part of the confirmed plan")
        if created_key:
            operation = substitute(operation, created_key)
        outcome = jira_port.apply_plan(
            port,
            jira_port.Plan([operation]),
            ctx.log,
            run,
            ctx.scope_id,
            plan_hash=plan.short_hash,
        )
        if not outcome.ok:
            return outcome
        completed += outcome.completed
        results.extend(outcome.results)
        if operation.kind == "create" and outcome.results:
            created_key = str(outcome.results[0].get("key"))
    return jira_port.Outcome("ok", completed, results)


def record(ctx: Context, key: str, draft: str) -> None:
    """Update local indexes only after all external operations succeeded."""
    doc = tables.parse(ctx.registry.read_text(encoding="utf-8"))
    doc.table.upsert(
        ctx.scope_id,
        {
            "Kind": "story",
            "Jira key": key,
            "Label": f"feat:{ctx.draft.stem}",
            "Entity property": PROPERTY,
            "Last published draft hash": hashing.draft_hash(draft),
            "State": "published",
        },
    )
    ctx.registry.write_text(doc.render(), encoding="utf-8")
    matrix = tables.parse(ctx.rtm.read_text(encoding="utf-8"))
    matrix.table.upsert(ctx.scope_id, {"Jira [sw-publish]": key})
    ctx.rtm.write_text(matrix.render(), encoding="utf-8")
    card = ctx.card.read_text(encoding="utf-8")
    ctx.card.write_text(
        frontmatter.update(
            card,
            {
                "status": "published",
                "home": "jira",
                "links": [f"https://example.atlassian.net/browse/{key}"],
            },
        ),
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "verify"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--feat", required=True)
    parser.add_argument("--scope")
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)
    try:
        ctx = context(Path(args.root).resolve(), args.feat, args.scope)
        errors = preconditions(ctx)
        if errors:
            raise PublishError("; ".join(errors))
        draft = ctx.draft.read_text(encoding="utf-8")
        if args.command == "verify":
            result = jira_diff.plan("", "", draft, scope_id=ctx.scope_id)
            print(
                json.dumps(
                    {
                        "confirm": confirmed(args.confirm or "", result),
                        "short_hash": result["short_hash"],
                    }
                )
            )
            return 0
        print(json.dumps({"scope_id": ctx.scope_id, "draft_hash": hashing.draft_hash(draft)}))
        return 0
    except (PublishError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
