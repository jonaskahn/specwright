#!/usr/bin/env python3
"""Build each public Specwright skill as a self-contained, reproducible zip.

The repository keeps one canonical ``skills/_shared`` tree. Packaging copies into each
public skill only the shared files listed for it in ``skills/_shared/bundle-map.json``
and rewrites ``../_shared/`` references to local ``_shared/`` so an uploaded folder never
depends on a sibling or the source checkout. Shipped HTML and CSS are minified (the source
stays readable). A skill over the map's file cap is refused, because the upload limit is a
file count.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

import bundle
import minify

SKILL_PREFIX = "sw-"
SHARED = "_shared"
SOURCE_REF = re.compile(r"(?<![\w.-])\.\./_shared/")
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".html", ".css", ".txt"}


def skill_sources(root: Path) -> list[Path]:
    skills = root / "skills"
    return sorted(
        p
        for p in skills.iterdir()
        if p.is_dir() and p.name.startswith(SKILL_PREFIX) and (p / "SKILL.md").is_file()
    )


def shared_folder(root: Path) -> Path:
    path = root / "skills" / SHARED
    if not path.is_dir():
        raise ValueError("skills/_shared is missing")
    return path


def _rewrite_text(path: Path) -> None:
    if path.suffix not in TEXT_SUFFIXES:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError:
        return
    rewritten = SOURCE_REF.sub("_shared/", text)
    if rewritten != text:
        path.write_text(rewritten, encoding="utf-8")


def bundle_skill(root: Path, source: Path, destination: Path) -> None:
    """Copy one public skill plus the shared tree, then make references local."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"destination exists: {destination}")
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )
    shared = shared_folder(root)
    for rel in bundle.shared_list(root, source.name):
        target = destination / SHARED / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(shared / rel, target)
    for path in sorted(destination.rglob("*")):
        if path.is_file():
            _rewrite_text(path)
            minify.minify_file(path)


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
        raise ValueError("no public skill folders found")
    if output.resolve() == root.resolve() or root.resolve().is_relative_to(output.resolve()):
        raise ValueError("output must not contain the source repository")
    # Preflight every skill so a collision or an oversize bundle leaves no partial set.
    for source in sources:
        bundle.shared_list(root, source.name)
        over = bundle.budget_error(root, source)
        if over:
            raise ValueError(over)
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
