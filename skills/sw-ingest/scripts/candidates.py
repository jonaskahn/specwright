#!/usr/bin/env python3
"""Plan, check and review candidate extraction done by several workers.

assign    split the snapshots not yet assigned into worker files of about 18,000 words each and
          record who reads what in 01-analysis/candidates/assignment.tsv
check     every snapshot assigned once, every citation resolves and cites only the worker's own
          snapshots, counts add up, claims are short summaries
conflicts same topic, different claim: both citations side by side, before any question is raised
show      one candidate with its exact cited text, copied by program
status    set one candidate to accepted, rejected, merged (--into) or back to raw

Workers write only their own file. Exit codes: 0 done or clean, 1 findings, 2 invalid request or
unreadable data, 3 the scope must be chosen.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
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

from kitlib import candidates, cite, workspace, writelog  # noqa: E402


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("assign", "check", "conflicts", "show", "status"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope")
        if name == "assign":
            cmd.add_argument("--target-words", type=int, default=candidates.TARGET_WORDS)
            cmd.add_argument("--dry-run", action="store_true")
        if name in ("show", "status"):
            cmd.add_argument("key", help="a candidate such as CAND-003.7")
        if name == "status":
            cmd.add_argument("value", choices=candidates.STATUSES)
            cmd.add_argument("--into", default="", help="the candidate a merged one joins")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, args.command in ("assign", "status"))
        base = workspace.scope_dir(root, scope)
        if args.command == "assign":
            if args.target_words < 1000:
                raise ValueError("--target-words must be at least 1000")
            existing = bool(candidates.read_assignment(base))
            rows, files = candidates.plan_assignment(
                base, scope, args.target_words, date.today().isoformat()
            )
            if not rows:
                print("nothing to assign: every snapshot already has a worker")
                return 0
            for worker in sorted({r["worker"] for r in rows}):
                mine = [r for r in rows if r["worker"] == worker]
                total = sum(int(r["words"]) for r in mine)
                print(f"{worker} {mine[0]['area']}: {len(mine)} snapshot(s), {total} words")
                for r in mine:
                    print(f"  {r['snapshot']} ({r['words']} words)")
            if args.dry_run:
                return 0
            target = candidates.folder(base) / candidates.ASSIGNMENT
            with writelog.operation(
                base / "_meta/write-log.md", "sw-ingest", "candidates-assign", scope
            ) as op:
                for path, text in files.items():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("x", encoding="utf-8", newline="") as handle:
                        handle.write(text)
                    op.wrote(path)
                previous = target.read_text(encoding="utf-8") if existing else ""
                candidates.write_text(target, previous + candidates.assignment_text(rows, existing))
                op.wrote(target)
            return 0
        if args.command == "check":
            problems = candidates.check(base)
            print("\n".join(problems) if problems else "candidates clean")
            return 1 if problems else 0
        if args.command == "conflicts":
            pairs = candidates.conflicts(base)
            for a, b in pairs:
                print(f"topic {a.topic}:")
                for x in (a, b):
                    print(f"  {x.key} [{x.status}] {x.claim}  <- {', '.join(x.citations)}")
            print(f"{len(pairs)} conflict(s)" if pairs else "no conflicting candidates")
            return 0
        if args.command == "show":
            found = candidates.item(base, args.key)
            print(f"{found.key} [{found.status}] {found.kind} / {found.topic}\n{found.claim}")
            sources = cite.Sources(base)
            for text in found.citations:
                one = cite.parse_one(text)
                print(f"\n{cite.stamp(sources, one)}\n{cite.quote(sources, one)}")
            return 0
        path, text = candidates.set_status(base, args.key, args.value, args.into)
        with writelog.operation(
            base / "_meta/write-log.md", "sw-ingest", "candidate-status", args.key
        ) as op:
            candidates.write_text(path, text)
            op.wrote(path)
        print(f"{args.key} is now {args.value}")
        return 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
