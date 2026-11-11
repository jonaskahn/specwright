#!/usr/bin/env python3
"""Install the public Specwright skills without overwriting existing rules."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import bundle
from package import bundle_skill, skill_sources


def _put_if_absent(path: Path, content: str, created: list[str], target: Path) -> None:
    if path.exists() or path.is_symlink():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path.relative_to(target)))


def install(
    root: Path, target: Path, copy_mirror: bool = False, profile: str = "extended"
) -> dict[str, list[str]]:
    sources = skill_sources(root)
    if not sources:
        raise ValueError("no public skill folders found")
    target = target.resolve()
    canonical = target / ".agents" / "skills"
    mirror = target / ".claude" / "skills"
    for source in sources:
        for base in (canonical, mirror):
            path = base / source.name
            if path.exists() or path.is_symlink():
                raise FileExistsError(f"refusing to replace existing skill: {path}")
    created: list[str] = []
    skipped: list[str] = []
    with tempfile.TemporaryDirectory(prefix="specwright-install-") as raw:
        staging = Path(raw)
        for source in sources:
            bundle_skill(root, source, staging / source.name, profile)
        canonical.mkdir(parents=True, exist_ok=True)
        mirror.mkdir(parents=True, exist_ok=True)
        for source in sources:
            destination = canonical / source.name
            shutil.copytree(staging / source.name, destination)
            created.append(str(destination.relative_to(target)))
            alias = mirror / source.name
            if copy_mirror or os.name == "nt":
                shutil.copytree(destination, alias)
            else:
                alias.symlink_to(
                    os.path.relpath(destination, alias.parent), target_is_directory=True
                )
            created.append(str(alias.relative_to(target)))
    rules = (root / "AGENTS.md").read_text(encoding="utf-8")
    agents = target / "AGENTS.md"
    if agents.exists() and agents.read_text(encoding="utf-8") != rules:
        skipped.append("AGENTS.md: existing project instructions preserved")
    _put_if_absent(agents, rules, created, target)
    project_rules = agents.read_text(encoding="utf-8")
    for name in ("CLAUDE.md", "GEMINI.md"):
        existing = target / name
        if existing.exists():
            skipped.append(f"{name}: existing instructions preserved")
        _put_if_absent(existing, project_rules, created, target)
    pointer = "# Project instructions\n\nRead and follow ../AGENTS.md.\n"
    _put_if_absent(target / ".github" / "copilot-instructions.md", pointer, created, target)
    return {"created": created, "preserved": skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--copy-mirror", action="store_true", help="copy instead of symlinking")
    parser.add_argument(
        "--profile",
        choices=bundle.PROFILES,
        default="extended",
        help="extended installs every diagram type (default); core installs the smaller set",
    )
    args = parser.parse_args(argv)
    try:
        print(json.dumps(install(args.root, args.target, args.copy_mirror, args.profile), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
