#!/usr/bin/env python3
"""Regenerate the shipped drawing examples from their fixtures and the canonical theme.

Every structured type ships one example page, ``skills/sw-spec/assets/<type>.html``,
rendered from ``fixtures/draw/<type>.json`` (business-analysis types from
``fixtures/refund/diagrams``). The four hand-edited template pages keep their own
drawing and only take the current theme. ``--check`` reports drift without writing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "sw-spec" / "scripts"
ASSETS = ROOT / "skills" / "sw-spec" / "assets"
sys.path.insert(0, str(SCRIPTS))

import render_diagram  # noqa: E402
from draw_types import LEGACY, STRUCTURED, TEMPLATES  # noqa: E402


def fixture(kind: str) -> Path:
    folder = "fixtures/refund/diagrams" if kind in LEGACY else "fixtures/draw"
    return ROOT / folder / f"{kind}.json"


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
        out[ASSETS / f"{kind}.html"] = page
        if kind in LEGACY:
            folder = ROOT / "fixtures" / "refund" / "diagrams"
            out[folder / f"{kind}.html"] = page
            if source is not None:
                out[folder / f"{kind}.mmd"] = source
    for kind in TEMPLATES:
        path = ASSETS / f"{kind}-template.html"
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
