"""Deterministic, section-aware three-way dry-runs and drift classification.

CLI exits: 0 no write, 1 apply, 2 invalid input, 3 sync needed, 4 conflict.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kitlib import frontmatter, hashing, markdown, schema, tables  # noqa: E402
from kitlib.jira_port import canonical_hash  # noqa: E402


def action(base, theirs, ours):
    if ours == theirs:
        return "no-op"
    if theirs == base:
        return "apply"
    if ours == base:
        return "keep-theirs"
    return "CONFLICT"


def by_section(md):
    body = frontmatter.parse(md).body
    return {
        name: markdown.normalise(section.text) for name, section in markdown.sections(body).items()
    }


def unified(theirs, ours):
    return "".join(
        difflib.unified_diff(
            (theirs + "\n").splitlines(True),
            (ours + "\n").splitlines(True),
            fromfile="Jira",
            tofile="draft",
        )
    )


def plan(
    base,
    theirs,
    ours,
    *,
    base_fields=None,
    their_fields=None,
    our_fields=None,
    scope_id="",
    jira_key="NEW",
    project="",
    sandbox=False,
    updated="",
    links=None,
    attachments=None,
    calls=None,
):
    """Hash all visible decisions and execution preconditions, not just the new draft."""
    b, t, o = map(by_section, (base, theirs, ours))
    rows = []
    names = list(schema.STORY_SECTIONS) + sorted(
        (b.keys() | t.keys() | o.keys()) - set(schema.STORY_SECTIONS)
    )
    for name in names:
        bv, tv, ov = b.get(name, ""), t.get(name, ""), o.get(name, "")
        act = action(bv, tv, ov)
        rows.append(
            {
                "section": name,
                "base": bv,
                "current": tv,
                "new": ov,
                "action": act,
                "diff": unified(tv, ov) if act in {"apply", "CONFLICT"} else "",
            }
        )
    fields = []
    bf, tf, of = base_fields or {}, their_fields or {}, our_fields or {}
    for name in sorted(bf.keys() | tf.keys() | of.keys()):
        bv, tv, ov = bf.get(name), tf.get(name), of.get(name)
        fields.append(
            {"field": name, "base": bv, "current": tv, "new": ov, "action": action(bv, tv, ov)}
        )
    result = {
        "scope_id": scope_id,
        "jira_key": jira_key,
        "project": project,
        "sandbox": sandbox,
        "draft_hash": hashing.draft_hash(ours),
        "updated": updated,
        "sections": rows,
        "fields": fields,
        "links": links or [],
        "attachments": attachments or [],
        "calls": calls or [],
    }
    result["plan_hash"] = canonical_hash(result)
    result["short_hash"] = result["plan_hash"][:8]
    result["exit_code"] = exit_code(result)
    return result


def exit_code(result):
    acts = {r["action"] for r in result["sections"] + result["fields"]}
    if "CONFLICT" in acts:
        return 4
    if "keep-theirs" in acts:
        return 3
    if "apply" in acts or result.get("links") or result.get("attachments") or result.get("calls"):
        return 1
    return 0


def render_plan(result):
    """Render _meta/publish-plan.md without turning cell content into extra columns."""
    lines = [
        "# Publish plan",
        "",
        f"Spec ID: {result['scope_id']}",
        *([f"Name: {result['name']}"] if result.get("name") else []),
        *([f"Aliases: {', '.join(result['aliases'])}"] if result.get("aliases") else []),
        f"Jira key: {result['jira_key']}",
        f"Target project: {result['project']}",
        f"Sandbox: {'yes' if result['sandbox'] else 'no'}",
        f"Draft hash: {result['draft_hash']}",
        f"Jira updated: {result['updated']}",
        f"Plan hash: {result['plan_hash']}",
        "",
        "## Fields",
        "",
    ]

    def display(value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True).replace("\n", " ")

    lines.append(
        tables.Table(
            ["Field", "Current", "New", "Action"],
            [
                [r["field"], display(r["current"]), display(r["new"]), r["action"]]
                for r in result["fields"]
            ],
        ).render()
    )
    lines.extend(
        [
            "## Sections",
            "",
            tables.Table(
                ["Section", "Action"], [[r["section"], r["action"]] for r in result["sections"]]
            ).render(),
        ]
    )
    for row in result["sections"]:
        if row["diff"]:
            fence = "~" * (
                max([len(line) for line in row["diff"].splitlines() if set(line) == {"~"}] + [2])
                + 1
            )
            lines.extend(
                [f"### {row['section']}", "", fence + "diff", row["diff"].rstrip("\n"), fence, ""]
            )
    for title, key in [
        ("Links to add", "links"),
        ("Attachments to add", "attachments"),
        ("Calls in order", "calls"),
    ]:
        lines.extend([f"## {title}", ""])
        lines.extend(f"{i}. {display(item)}" for i, item in enumerate(result[key], 1))
        if not result[key]:
            lines.append("None")
        lines.append("")
    lines.extend(
        ["## Confirmation", "", f"PUBLISH {result['scope_id']} {result['short_hash']}", ""]
    )
    return "\n".join(lines)


def classify(base, current):
    """Return all independent drift classes in a stable order; absent data stays absent."""
    found = []
    bf, cf = base.get("fields", base), current.get("fields", current)
    if any(bf.get(k) != cf.get(k) for k in ("description", "summary")):
        found.append("content-edited")
    if _status(bf.get("status")) != _status(cf.get("status")):
        found.append("status-changed")
    old_ids = {str(c.get("id")) for c in base.get("comments", [])}
    if any(str(c.get("id")) not in old_ids for c in current.get("comments", [])):
        found.append("comments-new")
    if bf.get("issuelinks", base.get("links")) != cf.get("issuelinks", current.get("links")):
        found.append("links-changed")
    if (
        current.get("deleted")
        or base.get("key") != current.get("key")
        or bf.get("project") != cf.get("project")
    ):
        found.append("moved/deleted")
    if base.get("linked_version") != current.get("linked_version"):
        found.append("linked-doc-version")
    if base.get("identity") != current.get("identity"):
        found.append("identity")
    return found


def _status(value):
    """Jira statuses arrive as objects; saved snapshots keep their display name."""
    return value.get("name") if isinstance(value, dict) else value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan"])
    for name in ("base", "theirs", "ours"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--scope-id", default="")
    args = parser.parse_args(argv)
    try:
        result = plan(
            *(getattr(args, n).read_text(encoding="utf-8") for n in ("base", "theirs", "ours")),
            scope_id=args.scope_id,
        )
        print(render_plan(result), end="")
        return result["exit_code"]
    except (OSError, ValueError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
