#!/usr/bin/env python3
"""Verify that the one skill carries the canonical runtime and embedded themes."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

STYLE_BLOCK = re.compile(r"(<style>)(.*?)(</style>)", re.S | re.I)
SVG_SHELL_EXTRA = "\nsvg {\n    max-width: none;\n    min-width: 960px;\n}"


class VendorError(Exception):
    """A canonical or vendored path cannot satisfy the copy contract."""


def skill_folder(root: Path) -> Path:
    path = root / "skills" / "sw-start"
    if not (path / "SKILL.md").is_file():
        raise VendorError("skills/sw-start/SKILL.md is missing")
    return path


def expected_copies(root: Path) -> dict[Path, Path]:
    """Return vendored destination to canonical source for every required copy."""
    skill = skill_folder(root)
    runtime = sorted((root / "lib" / "kitlib").glob("*.py"))
    if not runtime:
        raise VendorError("lib/kitlib has no canonical Python modules")
    copies = {skill / "scripts" / "kitlib" / source.name: source for source in runtime}
    copies[skill / "LICENSE"] = root / "LICENSE"
    standing = skill / "assets" / "standing-rules.md"
    if standing.parent.is_dir():
        copies[standing] = root / "AGENTS.md"
    return copies


def theme_shells(root: Path) -> list[Path]:
    assets = skill_folder(root) / "assets"
    return sorted(assets.glob("*.html")) if (assets / "theme.css").is_file() else []


def sync_themes(root: Path) -> list[str]:
    shells = theme_shells(root)
    if not shells:
        return []
    theme = (shells[0].parent / "theme.css").read_text(encoding="utf-8")
    updated: list[str] = []
    for shell in shells:
        text = shell.read_text(encoding="utf-8")
        if theme in text:
            continue
        match = STYLE_BLOCK.search(text)
        if match is None:
            raise VendorError(f"missing style block: {shell}")
        extra = SVG_SHELL_EXTRA if "min-width: 960px" in match.group(2) else ""
        replacement = theme + extra
        text = text[: match.start(2)] + replacement + text[match.end(2) :]
        if theme not in text:
            raise VendorError(f"failed to embed theme: {shell}")
        shell.write_text(text, encoding="utf-8")
        updated.append(str(shell))
    return updated


def check(root: Path) -> list[str]:
    problems: list[str] = []
    skill = skill_folder(root)
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
    vendored = skill / "scripts" / "kitlib"
    if not vendored.is_dir():
        problems.append(f"missing vendored runtime: {vendored}")
    else:
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
    vendored = skill_folder(root) / "scripts" / "kitlib"
    expected_runtime = {source.name for source in (root / "lib" / "kitlib").glob("*.py")}
    for path in sorted(vendored.iterdir()):
        if path.is_file() and path.name not in expected_runtime:
            path.unlink()
    written = [str(path) for path in copies]
    written.extend(sync_themes(root))
    return written


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
