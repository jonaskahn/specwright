#!/usr/bin/env python3
"""Per-task status: record what the code elsewhere proved, and let the story follow.

    forge.py status TASK-001-1 planned
    forge.py status TASK-001-1 in-progress
    forge.py status TASK-001-1 done --evidence "make test -> 42 passed, exit 0"
    forge.py status TASK-001-1 blocked --reason "BR-001 undefined for tiers above 3"
    forge.py plan --feat FEAT-NNN       mark every not-started task planned
    forge.py show --feat FEAT-NNN

Writes only the task's `Status:`, `Evidence:` and `Blocked because:` lines in
03-plan/FEAT-NNN.tasks.md and, when the status changes, the story's own condition:
`in-development` while any task is in-progress, `done` only when every task is done AND every
acceptance criterion has evidence, back to the accepted status otherwise. Exit codes: 0 written,
1 refused (no evidence, unknown task), 2 usage or unreadable data.
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

from kitlib import frontmatter, fsio, ids, markdown, workspace  # noqa: E402

STATES = ("not-started", "planned", "in-progress", "done", "blocked")
FIELDS = ("Status", "Evidence", "Blocked because")


def _rewrite_block(text: str, tid: str, values: dict) -> str:
    """Set or drop labelled lines inside one task block; everything else stays as written."""
    lines = text.splitlines()
    heading = re.compile(r"^###\s+" + re.escape(tid) + r"\b")
    start = end = None
    for number, line in enumerate(lines):
        if heading.match(line):
            start = number
        elif start is not None and re.match(r"^#{1,3}\s", line):
            end = number
            break
    if start is None:
        raise ValueError(f"no task block {tid}")
    end = len(lines) if end is None else end
    field = re.compile(r"^\s*-?\s*(" + "|".join(FIELDS) + r")\s*:")
    kept = [line for line in lines[start + 1 : end] if not field.match(line)]
    while kept and not kept[-1].strip():
        kept.pop()
    for name in FIELDS:
        if values.get(name):
            kept.append(f"{name}: {values[name]}")
    tail = lines[end:]
    return "\n".join([*lines[: start + 1], *kept, "", *tail]).rstrip("\n") + "\n"


def _criterion_evidence(story_body: str, blocks: dict) -> list:
    """ACs whose every covering task is done and has proof; the rest is listed here."""
    section = markdown.sections(story_body).get("Acceptance criteria")
    acs = markdown.ac_blocks(section)
    covering = {ac: [] for ac in acs}
    for tid, block in blocks.items():
        for ref in ids.find_refs(block.field_line("Traces to")):
            if ref.id in covering:
                covering[ref.id].append(tid)
    missing = []
    for ac in sorted(covering):
        tasks = covering[ac]
        if not tasks:
            missing.append(f"{ac}: no task covers it")
            continue
        for tid in tasks:
            state = markdown.task_progress(blocks[tid])
            if state != "done":
                missing.append(f"{ac}: {tid} is {state}")
            elif not blocks[tid].field_line("Evidence"):
                missing.append(f"{ac}: {tid} is done without Evidence")
    return missing


def sync_story(base: Path, feat: str) -> dict:
    """Recompute the story condition from the tasks; write it only when it changes."""
    tasks_path = base / "03-plan" / f"{feat}.tasks.md"
    story_path = base / "02-drafts" / f"{feat}.story.md"
    if not tasks_path.is_file() or not story_path.is_file():
        return {"story": "missing", "changed": False}
    blocks = markdown.task_blocks(frontmatter.parse(tasks_path.read_text(encoding="utf-8")).body)
    story = story_path.read_text(encoding="utf-8")
    parsed = frontmatter.parse(story)
    status = str((parsed.fm or {}).get("status", "draft"))
    states = {tid: markdown.task_progress(b) for tid, b in blocks.items()}
    open_tasks = [tid for tid, state in states.items() if state != "done"]
    missing = _criterion_evidence(parsed.body, blocks)
    if "in-progress" in states.values():
        condition = "in-development"
    elif (
        blocks
        and not open_tasks
        and not missing
        and status in ("ready-to-publish", "published", "ready-for-dev", "in-development")
    ):
        condition = "done"
    elif status == "done" and (open_tasks or missing):
        # A reopened task means the work is under way again, not that the story lost its
        # acceptance: keep it in development so the board shows why it is no longer done.
        condition = "in-development"
    else:
        condition = status
    changed = condition != status
    if changed:
        head, sep, body = story.partition("\n---\n")
        if re.search(r"^status:.*$", head, re.M):
            head = re.sub(r"^status:.*$", f"status: {condition}", head, count=1, flags=re.M)
        else:
            head += f"\nstatus: {condition}"
        fsio.atomic_write(story_path, head + sep + body)
    return {
        "story": condition,
        "previous": status,
        "changed": changed,
        "tasks": states,
        "open_tasks": sorted(open_tasks),
        "criteria_missing_evidence": missing,
    }


def mark_planned(root: Path, args) -> dict:
    """`plan [TASK]`: set planned on one task, or on every task of --feat."""
    item = args.task or args.feat
    if not item:
        raise ValueError("plan needs a TASK id or --feat FEAT-NNN")
    scope = workspace.resolve(root, args.scope, item, Path(args.cwd).resolve(), True)
    base = workspace.scope_dir(root, scope)
    if args.task:
        parsed_task = ids.parse_task(args.task.split(":")[-1])
        if parsed_task is None:
            raise ValueError(f"not a task id: {args.task}")
        feat, targets = f"FEAT-{parsed_task[0]:03d}", [args.task.split(":")[-1]]
    else:
        feat = args.feat.split(":")[-1]
        targets = None
    path = base / "03-plan" / f"{feat}.tasks.md"
    if not path.is_file():
        raise ValueError(f"no tasks file for {feat}")
    text = path.read_text(encoding="utf-8")
    blocks = markdown.task_blocks(frontmatter.parse(text).body)
    targets = targets or sorted(
        tid for tid, block in blocks.items() if markdown.task_progress(block) == "not-started"
    )
    for tid in targets:
        if tid not in blocks:
            raise ValueError(f"{feat} has no active task {tid}")
        text = _rewrite_block(text, tid, {"Status": "planned"})
    fsio.atomic_write(path, text)
    return {"feature": feat, "planned": targets, **sync_story(base, feat)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    status = sub.add_parser("status", help="record one task's state")
    status.add_argument("task")
    status.add_argument("state", choices=STATES)
    status.add_argument("--evidence", help="for done: the command and its result")
    status.add_argument("--reason", help="for blocked: what is missing")
    status.add_argument("--cwd", default=".")
    status.add_argument("--scope")
    every = sub.add_parser("plan", help="mark one task or all tasks planned")
    every.add_argument("task", nargs="?", help="one TASK id; omit for every active task")
    every.add_argument("--feat", help="with no task: the feature whose tasks are marked")
    every.add_argument("--cwd", default=".")
    every.add_argument("--scope")
    show = sub.add_parser("show", help="print every task's state and the story condition")
    show.add_argument("--feat", required=True)
    show.add_argument("--cwd", default=".")
    show.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        if args.command == "show":
            feat = args.feat.split(":")[-1]
            scope = workspace.resolve(root, args.scope, args.feat, cwd, False)
            print(
                json.dumps(
                    sync_story(workspace.scope_dir(root, scope), feat), indent=2, sort_keys=True
                )
            )
            return 0
        if args.command == "plan":
            data = mark_planned(root, args)
            print(json.dumps(data, indent=2, sort_keys=True))
            return 0
        tid = args.task.split(":")[-1]
        parsed_task = ids.parse_task(tid)
        if parsed_task is None:
            raise ValueError(f"not a task id: {args.task}")
        scope = workspace.resolve(root, args.scope, args.task, cwd, True)
        feat = f"FEAT-{parsed_task[0]:03d}"
        base = workspace.scope_dir(root, scope)
        path = base / "03-plan" / f"{feat}.tasks.md"
        if not path.is_file():
            raise ValueError(f"no tasks file for {feat}")
        text = path.read_text(encoding="utf-8")
        if tid not in markdown.task_blocks(frontmatter.parse(text).body):
            raise ValueError(f"{feat} has no active task {tid}")
        if args.state == "done" and not (args.evidence or "").strip():
            raise ValueError("done needs --evidence: the command and its result")
        if args.state == "blocked" and not (args.reason or "").strip():
            raise ValueError("blocked needs --reason")
        values = {
            "Status": args.state,
            "Evidence": (args.evidence or "").strip(),
            "Blocked because": (args.reason or "").strip(),
        }
        fsio.atomic_write(path, _rewrite_block(text, tid, values))
        data = sync_story(base, feat)
        print(json.dumps({"task": tid, **data}, indent=2, sort_keys=True))
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
