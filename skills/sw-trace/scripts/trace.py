#!/usr/bin/env python3
"""Expose trace maintenance without taking over evidence owned by other skills.

Exit codes: 0 clean, 1 findings, 2 usage or unreadable data, 4 ownership violation.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import rtm, workspace  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("rebuild", "check", "impact", "set"):
        cmd = sub.add_parser(command)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope")
        if command in ("impact", "set"):
            cmd.add_argument("id")
        if command == "set":
            cmd.add_argument("--column", required=True)
            cmd.add_argument("--value", required=True)
            cmd.add_argument("--as", dest="skill", required=True)
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run sw-init first")
        scope = workspace.resolve(
            root, args.scope, getattr(args, "id", None), cwd, args.command in ("set", "rebuild")
        )
        if args.command == "set":
            rtm.set_cell(root, scope, args.id, args.column, args.value, args.skill)
            print(json.dumps({"updated": rtm.qualify(args.id, scope), "column": args.column}))
            return 0
        if args.command == "impact":
            print(json.dumps(rtm.impact(root, args.id, scope), indent=2))
            return 0
        if args.command == "rebuild":
            rtm.rebuild(root, scope)
        findings = rtm.check(root, scope)
        for finding in findings:
            print(finding)
        return 1 if findings else 0
    except rtm.OwnershipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
