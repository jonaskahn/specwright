#!/usr/bin/env python3
"""Keep source skills aligned with the canonical ``skills/_shared`` tree.

Source skills reference shared material as ``../_shared/...`` and never vendor it.
Packaging is what embeds a local ``_shared/`` copy into each shipped skill.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SHARED = "_shared"


class VendorError(Exception):
    """The shared tree or a skill copy violates the copy contract."""


def skill_folders(root: Path) -> list[Path]:
    skills = root / "skills"
    return sorted(
        path for path in skills.glob("sw-*") if path.is_dir() and (path / "SKILL.md").is_file()
    )


def shared_folder(root: Path) -> Path:
    path = root / "skills" / SHARED
    if not path.is_dir():
        raise VendorError("skills/_shared is missing")
    if (path / "SKILL.md").exists():
        raise VendorError("skills/_shared must not be a registered skill")
    return path


def check(root: Path) -> list[str]:
    problems: list[str] = []
    try:
        shared = shared_folder(root)
    except VendorError as exc:
        return [str(exc)]
    if not (shared / "scripts" / "kitlib").is_dir():
        problems.append("skills/_shared/scripts/kitlib is missing")
    if not any((shared / "scripts").glob("*.py")):
        problems.append("skills/_shared has no capability scripts")
    for skill in skill_folders(root):
        if (skill / SHARED).exists():
            problems.append(f"source skill must not vendor _shared: {skill / SHARED}")
        if (skill / "scripts" / "kitlib").exists():
            problems.append(f"source skill must not vendor kitlib: {skill / 'scripts/kitlib'}")
        if (skill / "_shared").exists():
            problems.append(f"source skill must not vendor _shared: {skill / SHARED}")
    return problems


def write(root: Path) -> list[str]:
    # Source keeps one canonical copy; no per-skill vendoring is needed.
    shared_folder(root)
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verify the shared-source layout")
    group.add_argument("--write", action="store_true", help="validate; source needs no copies")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.write:
            for name in write(root):
                print(name)
            return 0
        problems = check(root)
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0
    except (OSError, VendorError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
