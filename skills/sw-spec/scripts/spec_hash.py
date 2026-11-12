#!/usr/bin/env python3
"""Recompute the `Draft hash:` line of a story after a body edit.

stamp   restamp the draft hash in place (idempotent; Identity is excluded from the hash)
check   exit 1 when the recorded hash differs from the current draft hash

Exit codes: 0 ok, 1 hash differs (check) or invalid input, 2 usage or file error.
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

from kitlib import fsio, hashing, ids  # noqa: E402


def _path(root: Path, feature: str) -> Path:
    if not ids.matches_type("feature", feature):
        raise ValueError(f"{feature} is not a feature ID such as FEAT-002")
    target = root / "02-drafts" / f"{feature}.story.md"
    if not target.is_file():
        raise ValueError(f"{target} does not exist")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("feature", help="feature ID such as FEAT-002")
    parser.add_argument("--stamp", action="store_true", help="write the fresh hash in place")
    parser.add_argument("--check", action="store_true", help="fail when the hash is stale")
    args = parser.parse_args(argv)
    try:
        target = _path(args.scope_root, args.feature)
        text = target.read_text(encoding="utf-8")
        current = hashing.draft_hash(text)
        if args.check:
            if hashing.needs_stamp(text):
                print(
                    f"{args.feature} is stale: Draft hash differs from {current}", file=sys.stderr
                )
                return 1
            print(f"{args.feature} {current}")
            return 0
        if not args.stamp:
            print(f"{args.feature} {current}")
            return 0
        updated = hashing.stamp(text)
        if updated != text:
            fsio.atomic_write(target, updated)
            print(f"{args.feature} {hashing.draft_hash(updated)}")
        else:
            print(f"{args.feature} {current} (unchanged)")
        return 0
    except (ValueError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1 if isinstance(exc, ValueError) else 2


if __name__ == "__main__":
    sys.exit(main())
