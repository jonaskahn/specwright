#!/usr/bin/env python3
"""Render validated offline HTML or standalone SVG. Exit 0 written, 2 invalid, 3 use prose."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
import draw_legacy
from draw_common import ParagraphRequired
from draw_page import standalone
from draw_types import LEGACY, MERMAID, STRUCTURED, TEMPLATES, TYPES

from kitlib.fsio import atomic_write


def module(kind):
    if kind not in STRUCTURED:
        raise ValueError("unknown structured type")
    return importlib.import_module("draw_types." + kind.replace("-", "_"))


def validate(spec):
    if (
            not isinstance(spec, dict)
            or not isinstance(spec.get("type"), str)
            or spec["type"] not in TYPES
    ):
        raise ValueError("choose one of the supported sw-draw types")
    kind = spec["type"]
    if kind in TEMPLATES:
        raise ValueError(
            f"{kind} is a template type; copy assets/{kind}-template.html "
            "and edit, then check offline/borders"
        )
    if kind in LEGACY:
        # The shared exception preserves the paragraph gate exit code across families.
        try:
            return draw_legacy.validate(spec)
        except draw_legacy.ParagraphRequired as exc:
            raise ParagraphRequired(str(exc)) from exc
    return module(kind).validate(spec)


def render(spec):
    validate(spec)
    result = (
        draw_legacy.render(spec) if spec["type"] in LEGACY else module(spec["type"]).render(spec)
    )
    return result


def layout(spec):
    validate(spec)
    return draw_legacy.layout(spec) if spec["type"] in LEGACY else module(spec["type"]).layout(spec)


def mermaid(spec):
    validate(spec)
    if spec["type"] not in MERMAID:
        return None
    return (
        draw_legacy.mermaid(spec) if spec["type"] in LEGACY else module(spec["type"]).mermaid(spec)
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="validated JSON, see the matching type reference")
    parser.add_argument(
        "output", type=Path, help="separate .html or .svg output; supported Mermaid sidecar"
    )
    args = parser.parse_args(argv)
    try:
        if (
                args.output.suffix not in {".html", ".svg"}
                or args.output.resolve() == args.spec.resolve()
        ):
            raise ValueError("output must be a separate .html or .svg file")
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        page, source = render(spec)
        output = standalone(page) if args.output.suffix == ".svg" else page
        # Preflight all sidecars before writing any artifact.
        paths = [args.output] + ([args.output.with_suffix(".mmd")] if source is not None else [])
        if any(p.resolve() == args.spec.resolve() or p.is_dir() for p in paths):
            raise ValueError("output or companion collides with input/directory")
        atomic_write(args.output, output)
        if source is not None:
            atomic_write(paths[1], source)
        print(args.output)
        return 0
    except ParagraphRequired as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
