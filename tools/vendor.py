#!/usr/bin/env python3
"""Mirror canonical runtime files into every self-contained skill folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from kitlib.schema import SKILL_PREFIX  # noqa: E402


class VendorError(Exception):
    """A canonical or vendored path cannot satisfy the copy contract."""


def skill_folders(root: Path) -> list[Path]:
    return sorted(
        path
        for path in (root / "skills").glob(f"{SKILL_PREFIX}*")
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def expected_copies(root: Path) -> dict[Path, Path]:
    """Return vendored destination to canonical source for every required copy."""
    copies: dict[Path, Path] = {}
    skills = skill_folders(root)
    runtime = sorted((root / "lib" / "kitlib").glob("*.py"))
    shared = sorted((root / "lib" / "shared-references").glob("*.md"))
    if not runtime:
        raise VendorError("lib/kitlib has no canonical Python modules")
    if not shared:
        raise VendorError("lib/shared-references has no canonical references")
    for skill in skills:
        for source in runtime:
            copies[skill / "scripts" / "kitlib" / source.name] = source
        for source in shared:
            copies[skill / "references" / source.name] = source
        copies[skill / "LICENSE"] = root / "LICENSE"
    standing = root / "skills" / "sw-init" / "assets" / "standing-rules.md"
    if standing.parent.is_dir():
        copies[standing] = root / "AGENTS.md"
    return copies


def theme_shells(root: Path) -> list[Path]:
    """Drawing shells that must embed assets/theme.css byte for byte."""
    assets = root / "skills" / "sw-draw" / "assets"
    return sorted(assets.glob("*.html")) if (assets / "theme.css").is_file() else []


def check(root: Path) -> list[str]:
    problems: list[str] = []
    for shell in theme_shells(root):
        theme = (shell.parent / "theme.css").read_text(encoding="utf-8")
        if theme not in shell.read_text(encoding="utf-8"):
            problems.append(f"stale embedded theme: {shell}")
    copies = expected_copies(root)
    if (root / "skills" / "_shared").exists():
        problems.append("skills/_shared must not exist")
    for destination, source in copies.items():
        if not source.is_file():
            problems.append(f"missing canonical file: {source}")
            continue
        if not destination.is_file():
            problems.append(f"missing vendored file: {destination}")
            continue
        if destination.read_bytes() != source.read_bytes():
            problems.append(f"divergent vendored file: {destination}")
    for skill in skill_folders(root):
        vendored = skill / "scripts" / "kitlib"
        if not vendored.is_dir():
            problems.append(f"missing vendored runtime: {vendored}")
            continue
        expected = {source.name for source in (root / "lib" / "kitlib").glob("*.py")}
        actual = {
            path.name
            for path in vendored.iterdir()
            if path.is_file() and path.name not in {"__pycache__"}
        }
        for name in sorted(actual - expected):
            problems.append(f"unexpected vendored file: {vendored / name}")
    return problems


def write(root: Path) -> list[str]:
    copies = expected_copies(root)
    for destination, source in copies.items():
        if not source.is_file():
            raise VendorError(f"missing canonical file: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    expected_runtime = {source.name for source in (root / "lib" / "kitlib").glob("*.py")}
    for skill in skill_folders(root):
        vendored = skill / "scripts" / "kitlib"
        if not vendored.is_dir():
            continue
        for path in sorted(vendored.iterdir()):
            if path.is_file() and path.name not in expected_runtime:
                path.unlink()
    return [str(path) for path in copies]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verify every vendored copy")
    group.add_argument("--write", action="store_true", help="refresh every vendored copy")
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
