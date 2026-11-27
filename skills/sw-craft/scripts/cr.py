#!/usr/bin/env python3
"""Open and check a change request for a published story: the only way to change its wording.

    cr.py open --affects FEAT-004 --title "Extend the refund window" [--delta file.md] [--cwd P]
    cr.py base --cr CR-001          re-record the target's current hash after a rebase
    cr.py check --cr CR-001         base_hash current, Delta rows valid, Must not change named
    cr.py list --affects FEAT-004   every CR on the target with its status and base state

A CR record carries `base_hash` (the target story's draft hash when it was opened), an
`affects` list and a Delta table: one row per target criterion with an action (add, change,
remove, keep) and a Source. Applying it is sw-craft's change path (`merge.py ship`, then
`merge.py finish`); this script writes and checks the record, never the target.
Exit codes: 0 ok, 1 check findings, 2 usage or file error.
"""

import argparse
import json
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, hashing, ids, markdown, workspace  # noqa: E402

ACTIONS = ("add", "change", "remove", "keep")
AC_ID = re.compile(r"AC-\d{3}-\d+")


def _cr_path(base: Path, cr: str) -> Path:
    matches = sorted((base / "records").glob(f"{cr}--*.md"))
    if not matches:
        raise ValueError(f"no CR record {cr}")
    if len(matches) > 1:
        raise ValueError(f"several records for {cr}")
    return matches[0]


def _target(base: Path, fm: dict) -> str:
    affects = [str(a).split(":")[-1] for a in fm.get("affects") or []]
    found = [a for a in affects if a.startswith("FEAT-")]
    if len(found) != 1:
        raise ValueError("a CR affects exactly one feature")
    return found[0]


def _delta(body: str) -> list[dict]:
    section = markdown.sections(body, level=3).get("Delta")
    rows, header = [], None
    for _, line in section.lines if section else []:
        text = line.strip()
        if not text.startswith("|"):
            continue
        cells = [c.strip() for c in text.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(text.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def check(base: Path, cr: str) -> dict:
    path = _cr_path(base, cr)
    parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
    if parsed.error or not parsed.fm:
        return {"cr": cr, "findings": [f"{path.name}: front matter unreadable"], "pass": False}
    fm = parsed.fm
    findings = []
    if str(fm.get("status")) not in ("proposed", "in-review", "approved"):
        findings.append(f"status is {fm.get('status')}; only an open CR is applied")
    target = _target(base, fm)
    story = base / "02-drafts" / f"{target}.story.md"
    if not story.is_file():
        return {"cr": cr, "target": target, "findings": [f"{target} has no story"], "pass": False}
    text = story.read_text(encoding="utf-8")
    current = hashing.draft_hash(text)
    if fm.get("base_hash") != current:
        findings.append(f"{target} changed since {cr} was opened; cr.py base --cr {cr} rebases it")
    acs = markdown.ac_blocks(
        markdown.sections(frontmatter.parse(text).body).get("Acceptance criteria")
    )
    rows = _delta(parsed.body)
    if not rows:
        findings.append("Delta table is empty")
    for row in rows:
        tid, action, source = (
            row.get("target", ""),
            row.get("action", "").lower(),
            row.get("source", ""),
        )
        if action not in ACTIONS:
            findings.append(f"{tid or 'new'}: action must be one of {', '.join(ACTIONS)}")
            continue
        if action in ("change", "remove", "keep") and tid not in acs:
            findings.append(f"{tid}: not an active criterion of {target}")
        if action == "add" and tid not in ("new", "-", ""):
            findings.append(f"{tid}: an added criterion has target 'new'")
        if action in ("add", "change") and not (AC_ID.findall(source) or source.strip()):
            findings.append(f"{tid or 'new'}: {action} needs a source (the wording it comes from)")
        if action == "remove" and not source.strip():
            findings.append(f"{tid}: remove needs a reason in Source")
    keep = markdown.sections(parsed.body, level=3).get("Must not change")
    keep_ids = AC_ID.findall(keep.text) if keep else []
    if not keep_ids:
        findings.append("Must not change lists no target criterion (regression guard)")
    findings += [
        f"Must not change: {k} is not an active criterion of {target}"
        for k in keep_ids
        if k not in acs
    ]
    return {
        "cr": cr,
        "target": target,
        "status": fm.get("status"),
        "rows": rows,
        "keep": keep_ids,
        "findings": findings,
        "pass": not findings,
    }


def open_cr(base: Path, args) -> dict:
    scope = str(workspace.load(base / "project.yaml")["scope"])
    target = args.affects.split(":")[-1]
    story = base / "02-drafts" / f"{target}.story.md"
    if not story.is_file():
        raise ValueError(f"{target} has no story to change")
    text = story.read_text(encoding="utf-8")
    status = str((frontmatter.parse(text).fm or {}).get("status"))
    if status not in ("published", "ready-for-dev"):
        raise ValueError(
            f"{target} is {status}; an unpublished story is edited in place and needs no CR"
        )
    delta = (
        Path(args.delta).read_text(encoding="utf-8").strip()
        if args.delta
        else (
            "| Target | Action | Source |\n| --- | --- | --- |\n"
            "| AC-<n>-1 | change | <the new wording's source> |\n"
            "| new | add | <the new criterion> |\n"
        )
    )
    number = ids.next_id("CR", ids.taken_ids(base))
    fm = {
        "id": number,
        "type": "cr",
        "title": args.title,
        "aliases": [],
        "scope": scope,
        "status": "proposed",
        "affects": [f"{scope}:{target}"],
        "base_hash": hashing.draft_hash(text),
        "publish": "pending",
    }
    body = (
        f"# {args.title}\n\n## Delta\n\n{delta}\n\n"
        "## Must not change\n\n"
        "<target criteria that stay as they are — regression tests stay green>\n\n"
        "## Proposed wording\n\n<the new criteria, rules and NFR lines, verbatim>\n"
    )
    path = base / "records" / ids.record_filename(number, args.title)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(frontmatter.render(fm, body))
    return {"cr": number, "target": target, "base_hash": fm["base_hash"], "path": path.name}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    opened = sub.add_parser("open", help="create a CR record for a published story")
    opened.add_argument("--affects", required=True)
    opened.add_argument("--title", required=True)
    opened.add_argument("--delta", help="a Markdown file holding the Delta table")
    for name, help_text in (
        ("base", "re-record base_hash"),
        ("check", "check the record"),
        ("list", "list CRs"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        if name == "list":
            cmd.add_argument("--affects")
        else:
            cmd.add_argument("--cr", required=True)
    for cmd in (opened, *[a for a in sub.choices.values() if a is not opened]):
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        ref = args.affects or args.cr
        scope = workspace.resolve(root, args.scope, ref, cwd, args.command in ("open", "base"))
        base = workspace.scope_dir(root, scope)
        if args.command == "open":
            print(json.dumps(open_cr(base, args), indent=2, sort_keys=True))
            return 0
        if args.command == "base":
            path = _cr_path(base, args.cr)
            text = path.read_text(encoding="utf-8")
            fm = frontmatter.parse(text).fm or {}
            target = _target(base, fm)
            story = (base / "02-drafts" / f"{target}.story.md").read_text(encoding="utf-8")
            digest = hashing.draft_hash(story)
            head, sep, body = text.partition("\n---\n")
            head = re.sub(r"^base_hash:.*$", f"base_hash: {digest}", head, count=1, flags=re.M)
            path.write_text(head + sep + body, encoding="utf-8")
            print(json.dumps({"cr": args.cr, "target": target, "base_hash": digest}))
            return 0
        if args.command == "list":
            rows = []
            for path in sorted((base / "records").glob("CR-*.md")):
                fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
                if args.affects and f"{scope}:{args.affects.split(':')[-1]}" not in (
                    fm.get("affects") or []
                ):
                    continue
                rows.append(
                    {
                        "cr": fm.get("id"),
                        "status": fm.get("status"),
                        "publish": fm.get("publish"),
                        "affects": fm.get("affects"),
                    }
                )
            print(json.dumps(rows, indent=2))
            return 0
        result = check(base, args.cr)
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
