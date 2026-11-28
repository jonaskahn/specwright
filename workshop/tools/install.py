#!/usr/bin/env python3
"""Install the public Specwright skills and command wrappers. Does not write agent files."""

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


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _previous(base: Path, root: Path) -> list[Path]:
    """Preflight all old skills, including retired names; never follow links on deletion."""
    found = []
    for path in sorted(base.glob("sw-*")):
        if not path.is_symlink():
            if root.resolve().is_relative_to(path.resolve()):
                raise ValueError(f"refusing to delete the skill source: {path}")
            source = root / "skills" / path.name
            if source.exists() and source.resolve().is_relative_to(path.resolve()):
                raise ValueError(f"refusing to delete the skill source: {path}")
        found.append(path)
    return found


def install(
    root: Path, target: Path, copy_mirror: bool = False, profile: str = "extended"
) -> dict[str, list[str]]:
    sources = skill_sources(root)
    if not sources:
        raise ValueError("no public skill folders found")
    target = target.resolve()
    canonical = target / ".agents" / "skills"
    mirror = target / ".claude" / "skills"
    previous = []
    new_paths = []
    command_source = root / "commands"
    command_files = sorted(command_source.glob("sw-*.md"))
    for base in (canonical, mirror):
        previous.extend(_previous(base, root))
        previous.extend(_previous(base.parent / "commands", root))
        new_paths.extend(base / source.name for source in sources)
        new_paths.extend(base.parent / "commands" / cmd.name for cmd in command_files)
    created: list[str] = []
    with tempfile.TemporaryDirectory(prefix="specwright-install-") as raw:
        staging = Path(raw)
        for source in sources:
            bundle_skill(root, source, staging / source.name, profile)
        # Read commands before moving old entries (the source can be a local checkout).
        commands = {p.name: p.read_text(encoding="utf-8") for p in command_files}
        backups = []
        writing = False
        try:
            for path in previous:
                backup = Path(tempfile.mkdtemp(prefix=".specwright-backup-", dir=path.parent))
                os.replace(path, backup / "item")
                backups.append((path, backup))
            writing = True
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
            for base in (canonical, mirror):
                out = base.parent / "commands"
                for name, text in commands.items():
                    out.mkdir(parents=True, exist_ok=True)
                    path = out / name
                    path.write_text(
                        text.replace("${CLAUDE_PLUGIN_ROOT}/skills/", base.as_posix() + "/"),
                        encoding="utf-8",
                    )
                    created.append(str(path.relative_to(target)))
        except Exception:
            if writing:
                for path in new_paths:
                    _remove(path)
            for path, backup in reversed(backups):
                os.replace(backup / "item", path)
                backup.rmdir()
            raise
        else:
            for _, backup in backups:
                shutil.rmtree(backup)
    return {
        "created": created,
        "removed": [str(p.relative_to(target)) for p in previous],
        "preserved": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
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
