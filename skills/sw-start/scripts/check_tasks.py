#!/usr/bin/env python3
"""Check that a feature's tasks cover its criteria and still match its story.

Exit codes: 0 pass, 1 findings, 2 usage or unreadable data. With --mark-ready a passing check
sets the tasks file status to ready; that records coverage, not human approval.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse

from kitlib import frontmatter, fsio, hashing, ids, markdown, workspace  # noqa: E402

APPROVED = ("ready-to-publish", "published", "ready-for-dev")


def check(base, feat):
    findings = []
    story = base / "02-drafts" / f"{feat}.story.md"
    tasks_path = base / "03-plan" / f"{feat}.tasks.md"
    if not story.is_file():
        return None, [f"{feat}: story draft not found"], None
    parsed = frontmatter.parse(story.read_text(encoding="utf-8"))
    status = str((parsed.fm or {}).get("status", "unknown"))
    if status not in APPROVED:
        findings.append(f"{feat}: status is {status}; review it with sw-review before planning")
    if not tasks_path.is_file():
        return tasks_path, [*findings, f"{feat}: no tasks file at 03-plan/{feat}.tasks.md"], None
    text = tasks_path.read_text(encoding="utf-8")
    tp = frontmatter.parse(text)
    if tp.error or not tp.fm:
        return tasks_path, [*findings, f"tasks file front matter: {tp.error or 'missing'}"], None
    current = hashing.draft_hash(story.read_text(encoding="utf-8"))
    if tp.fm.get("spec_hash") != current:
        findings.append("tasks are stale: spec_hash differs from the current story")
    section = markdown.sections(parsed.body).get("Acceptance criteria")
    acs = set(markdown.ac_blocks(section))
    blocks = markdown.task_blocks(tp.body)
    removed = set(markdown.task_tombstones(tp.body))
    covered = set()
    for tid, block in blocks.items():
        refs = ids.find_refs(block.field_line("Traces to"))
        if not refs:
            findings.append(f"{tid}: Traces to is empty")
        for ref in refs:
            if ref.id.startswith("AC-"):
                covered.add(ref.id)
                if ref.id not in acs:
                    findings.append(f"{tid}: traces to {ref.id}, which is not an active criterion")
        if not block.field_line("Done when"):
            findings.append(f"{tid}: Done when is empty")
    for ac in sorted(acs - covered):
        findings.append(f"{ac}: no task covers this criterion")
    number = ids.feat_number(feat)
    for tid in [*blocks, *removed]:
        parsed_id = ids.parse_task(tid)
        if parsed_id is None or parsed_id[0] != number:
            findings.append(f"{tid}: task number does not belong to {feat}")
    return tasks_path, findings, tp


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--feat", required=True)
    parser.add_argument("--mark-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run sw-init first")
        feat = ids.story_alias(args.feat).split(":")[-1]
        if not ids.matches_type("feature", feat):
            raise ValueError(f"not a feature id: {args.feat}")
        scope = workspace.resolve(root, args.scope, args.feat, cwd, args.mark_ready)
        base = workspace.scope_dir(root, scope)
        path, findings, parsed = check(base, feat)
        for line in findings:
            print(line)
        if findings:
            return 1
        if args.mark_ready:
            parsed.fm["status"] = "ready"
            fsio.atomic_write(path, frontmatter.render(parsed.fm, parsed.body))
            print(f"{feat}: tasks marked ready (coverage only; not human approval)")
        else:
            print(f"{feat}: tasks cover every criterion")
        return 0
    except (OSError, ValueError, workspace.WorkspaceError, workspace.AskUser) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
