#!/usr/bin/env python3
"""Print the illustration chip for one feature, and record a dismissal.

Exit 0 when the story can be read. Exit 2 on usage or file errors.
A dismissal writes illustration and illustration_reason in front matter only.
--json also writes _meta/work/illustration-FEAT-NNN.json.
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

from kitlib import fsio, illustration, workspace  # noqa: E402


def _base(scope_root: Path | None, cwd: Path) -> Path:
    if scope_root is not None:
        if not scope_root.is_dir():
            raise ValueError(f"{scope_root} is not a directory")
        return scope_root
    root = workspace.find_root(cwd)
    if root is None:
        raise ValueError("no workspace; pass --scope-root")
    scope = workspace.resolve(root, cwd=cwd)
    return workspace.scope_dir(root, scope)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", help="feature ID such as FEAT-002")
    parser.add_argument("--scope-root", type=Path, help="project directory that holds 02-drafts/")
    parser.add_argument("--cwd", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true", help="write the chip under _meta/work/")
    parser.add_argument("--dismiss", help="record illustration: none with this reason")
    args = parser.parse_args(argv)
    try:
        base = _base(args.scope_root, args.cwd)
        if args.dismiss is not None:
            result = illustration.dismiss(base, args.feature, args.dismiss)
        else:
            result = illustration.state(base, args.feature)
        print(illustration.render_text(result), end="")
        if args.json:
            target = base / "_meta/work" / f"illustration-{result['id']}.json"
            fsio.atomic_write(target, json.dumps(result, indent=2, sort_keys=True) + "\n")
            print(target)
        return 0
    except (OSError, UnicodeError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
