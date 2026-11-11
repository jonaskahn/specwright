#!/usr/bin/env python3
"""Check task coverage; --mark-ready records coverage, never human approval.

Exit codes: 0 pass, 1 findings, 2 usage or unreadable data.
"""

import argparse
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _source_shared if _source_shared.is_dir() else _local_shared
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, fsio, ids, task_validation, workspace  # noqa: E402

APPROVED = task_validation.APPROVED
check = task_validation.check


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
            raise ValueError("no workspace; run the sw-start workspace setup first")
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
