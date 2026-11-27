#!/usr/bin/env python3
"""Check and total the INVEST tables of idea briefs.

check   validate the table format of the given briefs
totals  pass, fail and unknown per brief and per letter for every brief in a project

Exit codes: 0 clean, 1 a table is malformed, 2 usage or unreadable data, 3 the scope must be chosen.
"""

from __future__ import annotations

import argparse
import json
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

from kitlib import frontmatter, invest, workspace  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check")
    check.add_argument("files", nargs="+", type=Path)
    totals = sub.add_parser("totals")
    totals.add_argument("--cwd", default=".")
    totals.add_argument("--scope")
    totals.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            bad = 0
            for path in args.files:
                body = frontmatter.parse(path.read_text(encoding="utf-8")).body
                found = invest.parse(body)[1]
                for problem in found:
                    print(f"{path}: {problem}")
                bad += len(found)
            if not bad:
                print("INVEST tables clean")
            return 1 if bad else 0
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, False)
        rows = invest.board(workspace.scope_dir(root, scope))
        if args.format == "json":
            print(json.dumps(rows, indent=1))
        else:
            for item in rows:
                print(f"{item['idea']} ({item['rows']} features) {item['title']}")
                for letter, count in item["totals"].items():
                    print(f"  {letter}: " + ", ".join(f"{n} {k}" for k, n in count.items()))
                for problem in item["problems"]:
                    print(f"  problem: {problem}")
            if not rows:
                print("no idea brief has an INVEST table yet")
        return 1 if any(item["problems"] for item in rows) else 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (OSError, UnicodeError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
