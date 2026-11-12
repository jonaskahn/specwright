#!/usr/bin/env python3
"""Keep each skill's ``_shared/`` copy identical to the canonical ``skills/_shared`` tree.

``skills/_shared`` is the one place shared code and references are edited. Hosts such as
``npx skills add`` install a skill folder on its own, so every ``skills/sw-*`` folder carries
a committed ``_shared/`` holding exactly the files ``skills/_shared/bundle-map.json`` lists
for it (the same list the zip packaging ships). ``--write`` regenerates the copies and
``--check`` fails on a missing, extra or different file.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bundle  # noqa: E402

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


def expected_files(root: Path, skill: Path) -> list[str]:
    """Shared-relative files the skill must carry, from the bundle map."""
    try:
        return bundle.shared_list(root, skill.name)
    except bundle.BundleError as exc:
        raise VendorError(str(exc)) from exc


def actual_files(skill: Path) -> set[str]:
    folder = skill / SHARED
    if not folder.is_dir():
        return set()
    return {
        p.relative_to(folder).as_posix()
        for p in folder.rglob("*")
        if p.is_file() and not bundle.is_junk(p.relative_to(folder))
    }


def drift(root: Path, skill: Path) -> list[str]:
    """Problems between one skill's ``_shared`` copy and the canonical files."""
    shared = shared_folder(root)
    wanted = expected_files(root, skill)
    have = actual_files(skill)
    problems = [f"{skill.name}: _shared/{rel} is missing" for rel in wanted if rel not in have]
    problems += [f"{skill.name}: _shared/{rel} is not mapped" for rel in sorted(have - set(wanted))]
    for rel in wanted:
        copy = skill / SHARED / rel
        if rel in have and copy.read_bytes() != (shared / rel).read_bytes():
            problems.append(f"{skill.name}: _shared/{rel} differs from skills/_shared/{rel}")
    return problems


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
        if (skill / "scripts" / "kitlib").exists():
            problems.append(f"source skill must not vendor kitlib: {skill / 'scripts/kitlib'}")
        try:
            problems.extend(drift(root, skill))
        except VendorError as exc:
            problems.append(str(exc))
    return problems


def write(root: Path) -> list[str]:
    """Rebuild each out-of-date ``_shared`` copy; return the names of the skills changed."""
    shared = shared_folder(root)
    changed: list[str] = []
    for skill in skill_folders(root):
        if not drift(root, skill):
            continue
        shutil.rmtree(skill / SHARED, ignore_errors=True)
        for rel in expected_files(root, skill):
            target = skill / SHARED / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(shared / rel, target)
        changed.append(skill.name)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="fail when a skill's _shared drifts")
    group.add_argument("--write", action="store_true", help="regenerate each skill's _shared")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.write:
            for name in write(root):
                print(f"updated {name}")
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
