#!/usr/bin/env python3
"""Commit a skill command's changes to the spec folder and push when a remote is set up.

  commit   stage only this project's spec files, commit them, then push (never forced)
  mode     show or set how far it goes: push (default), commit, off

Exit codes: 0 committed, nothing to commit, or skipped (off, no git); 2 usage or unreadable
workspace; 3 not committed (a merge or rebase is open, a hook or the identity refused);
4 committed but the push failed (the commit stands; fix the remote, then run `commit` again).
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse

from kitlib import checkpoint, workspace  # noqa: E402

EXIT_ERROR = 2


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope", help="the project; needed at a program root")
        return cmd

    run = add("commit", "commit the project's spec changes, then push")
    run.add_argument("--skill", required=True, help="the skill that ran, for the message")
    run.add_argument("--subject", required=True, help="what changed, in a few words")
    mode = add("mode", "show or set the checkpoint mode")
    mode.add_argument("--set", dest="value", choices=list(checkpoint.MODES))
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run the sw-start workspace setup first")
        scope = None
        if args.scope or workspace.mode_of(root) == "flat":
            scope = workspace.resolve(root, args.scope, None, cwd, True)
        if args.command == "mode":
            value = checkpoint.set_mode(root, scope, args.value) if args.value else None
            print(value or checkpoint.mode_for(root, scope))
            return 0
        result = checkpoint.commit(root, scope, args.skill, args.subject)
        print(result.line())
        return result.exit_code
    except (ValueError, OSError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
