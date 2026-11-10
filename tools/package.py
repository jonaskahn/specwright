#!/usr/bin/env python3
"""Build standalone skills with their shared library and optional reproducible zip files."""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from kitlib.schema import SKILL_PREFIX  # noqa: E402


def skill_sources(root: Path) -> list[Path]:
    return sorted(
        p
        for p in (root / "skills").iterdir()
        if p.is_dir() and p.name.startswith(SKILL_PREFIX) and (p / "SKILL.md").is_file()
    )


def bundle_skill(root: Path, source: Path, destination: Path) -> None:
    """Only build into a new directory; never erase an existing installation."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"destination exists: {destination}")
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    scripts = destination / "scripts"
    scripts.mkdir(exist_ok=True)
    vendored = scripts / "kitlib"
    if vendored.exists():
        shutil.rmtree(vendored)
    shutil.copytree(
        root / "lib" / "kitlib", vendored, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    shared = root / "skills" / "_shared" / "references"
    refs = destination / "references"
    refs.mkdir(exist_ok=True)
    if shared.exists():
        for reference in shared.glob("*.md"):
            if not (refs / reference.name).exists():
                shutil.copyfile(reference, refs / reference.name)
    shutil.copyfile(root / "LICENSE", destination / "LICENSE")


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
    sources = skill_sources(root)
    if not sources:
        raise ValueError("no skill folders found")
    if output.resolve() == root.resolve() or root.resolve().is_relative_to(output.resolve()):
        raise ValueError("output must not contain the source repository")
    # Preflight every path so a collision cannot leave a partial set of packages.
    for source in sources:
        paths = [output / source.name]
        if zipped:
            paths.append(output / f"{source.name}.zip")
        for path in paths:
            if path.exists() or path.is_symlink():
                raise FileExistsError(f"output exists: {path}; choose a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    built = []
    for source in sources:
        destination = output / source.name
        bundle_skill(root, source, destination)
        built.append(destination)
        if zipped:
            zip_skill(destination, output / f"{source.name}.zip")
    return built


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
