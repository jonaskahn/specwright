#!/usr/bin/env python3
"""Build the one self-contained Specwright skill and its reproducible zip file."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path


def skill_folder(root: Path) -> Path:
    path = root / "skills" / "sw-start"
    if not (path / "SKILL.md").is_file():
        raise ValueError("skills/sw-start/SKILL.md is missing")
    return path


def bundle_skill(root: Path, destination: Path) -> None:
    """Copy the self-contained skill folder without mutating its contents."""
    source = skill_folder(root)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"destination exists: {destination}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def zip_skill(folder: Path, target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(str(path.relative_to(folder.parent)), (2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def build(root: Path, output: Path, zipped: bool = False) -> list[Path]:
    source = skill_folder(root)
    if output.resolve() == root.resolve() or root.resolve().is_relative_to(output.resolve()):
        raise ValueError("output must not contain the source repository")
    paths = [output / source.name]
    if zipped:
        paths.append(output / f"{source.name}.zip")
    for path in paths:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"output exists: {path}; choose a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    destination = output / source.name
    bundle_skill(root, destination)
    if zipped:
        zip_skill(destination, output / f"{source.name}.zip")
    return [destination]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--zip", action="store_true", dest="zipped")
    args = parser.parse_args(argv)
    try:
        for path in build(args.root, args.out, args.zipped):
            print(path)
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
