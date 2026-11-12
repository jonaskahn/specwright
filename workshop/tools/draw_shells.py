#!/usr/bin/env python3
"""Regenerate the shipped drawing examples from their fixtures and the canonical theme.

Every structured type has one example page, rendered from ``workshop/fixtures/draw/<type>.json``
(business-analysis types from ``workshop/fixtures/refund/diagrams``). Core and extended types keep
theirs in ``skills/sw-spec/assets/<type>.html``; the types parked under ``extras/sw-spec``
keep theirs, their fixtures and the four hand-edited template pages there. Templates keep
their own drawing and only take the current theme. ``--check`` reports drift without writing.

Rendering always runs against a merged copy of the skill and ``extras/sw-spec`` so every
type in the closed roster is available, whatever the shipped skill carries.
"""

from __future__ import annotations

import argparse
import atexit
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "sw-spec"
EXTRAS = ROOT / "extras" / "sw-spec"
ASSETS = SKILL / "assets"


def full_tree() -> Path:
    """A temporary copy of the skill with ``extras/sw-spec`` laid over it."""
    tmp = Path(tempfile.mkdtemp(prefix="specwright-full-"))
    atexit.register(shutil.rmtree, tmp, True)
    skills = tmp / "skills"
    skills.mkdir()
    full = skills / "sw-spec"
    shutil.copytree(SKILL, full, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    for part in ("assets", "references", "scripts"):
        shutil.copytree(EXTRAS / part, full / part, dirs_exist_ok=True)
    (skills / "_shared").symlink_to(ROOT / "skills" / "_shared", target_is_directory=True)
    return full


FULL = full_tree()
SCRIPTS = FULL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_diagram  # noqa: E402
from draw_types import CORE, EXTENDED, LEGACY, STRUCTURED, TEMPLATES  # noqa: E402


def fixture(kind: str) -> Path:
    if kind in LEGACY:
        return ROOT / "workshop/fixtures/refund/diagrams" / f"{kind}.json"
    shipped = ROOT / "workshop/fixtures/draw" / f"{kind}.json"
    return shipped if shipped.is_file() else EXTRAS / "fixtures/draw" / f"{kind}.json"


def asset_path(kind: str) -> Path:
    """Where a type's example page lives: the skill when it ships, else extras."""
    name = f"{kind}-template.html" if kind in TEMPLATES else f"{kind}.html"
    base = ASSETS if kind in CORE or kind in EXTENDED else EXTRAS / "assets"
    return base / name


def indent(text: str, spaces: int) -> str:
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def restyle(page: str, theme: str) -> str:
    """Give a hand-edited template page the current theme in <head> and in its SVG."""
    page = re.sub(
        r"(<head>.*?<style>).*?(</style>)",
        lambda m: m.group(1) + theme + m.group(2),
        page,
        count=1,
        flags=re.S,
    )
    return re.sub(
        r"(<svg\b.*?<style>).*?(</style>)",
        lambda m: m.group(1) + "\n" + indent(theme.strip("\n"), 16) + "\n" + " " * 12 + m.group(2),
        page,
        count=1,
        flags=re.S,
    )


def expected() -> dict[Path, str]:
    theme = (ASSETS / "theme.css").read_text(encoding="utf-8")
    out: dict[Path, str] = {}
    for kind in STRUCTURED:
        spec = json.loads(fixture(kind).read_text(encoding="utf-8"))
        page, source = render_diagram.render(spec)
        out[asset_path(kind)] = page
        if kind in LEGACY:
            folder = ROOT / "workshop" / "fixtures" / "refund" / "diagrams"
            out[folder / f"{kind}.html"] = page
            if source is not None:
                out[folder / f"{kind}.mmd"] = source
    for kind in TEMPLATES:
        path = asset_path(kind)
        out[path] = restyle(path.read_text(encoding="utf-8"), theme)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="rewrite stale examples")
    mode.add_argument("--check", action="store_true", help="exit 1 when an example is stale")
    args = parser.parse_args(argv)
    stale = []
    for path, content in expected().items():
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        if current != content:
            stale.append(path)
            if args.write:
                path.write_text(content, encoding="utf-8")
    for path in stale:
        print(("wrote " if args.write else "stale ") + str(path.relative_to(ROOT)))
    return 1 if stale and args.check else 0


if __name__ == "__main__":
    sys.exit(main())
