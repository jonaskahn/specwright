#!/usr/bin/env python3
"""Rewrite story and epic documents onto the current front matter contract.

Exit codes: 0 migrated, 1 one or more files were refused, 2 usage or workspace error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import fm_migrate, workspace  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--scope")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = workspace.find_root(args.root.resolve())
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, cwd=args.root.resolve(), write=not args.dry_run)
        written, refused = fm_migrate.migrate_tree(
            workspace.scope_dir(root, scope), dry_run=args.dry_run
        )
    except (OSError, ValueError, workspace.WorkspaceError, workspace.AskUser) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for rel in written:
        print(("would write " if args.dry_run else "wrote ") + rel)
    for rel in refused:
        print(f"refused {rel}", file=sys.stderr)
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
