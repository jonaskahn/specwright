#!/usr/bin/env python3
"""Reserve the next epic in one scope without replacing an existing file.

Exit codes: 0 created, 1 invalid content or allocation conflict, 2 usage or file error.
The scope-root argument is an already resolved project directory, not a program root.
"""

from __future__ import annotations

import argparse
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

from kitlib import epics  # noqa: E402


def create(root, scope, title, scopes=None, template=None):
    template = template or _here.parent / "assets" / "epic.md"
    if not template.is_file():
        raise ValueError("template unavailable; provide --template pointing to assets/epic.md")
    return epics.create(root, scope, title, scopes, template.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--scopes", help="comma-separated projects taking part, home first")
    parser.add_argument("--template", type=Path)
    args = parser.parse_args(argv)
    try:
        participants = [s.strip() for s in args.scopes.split(",")] if args.scopes else None
        print(create(args.scope_root, args.scope, args.title, participants, args.template))
        return 0
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
