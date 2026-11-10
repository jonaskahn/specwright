"""Inert text and SVG primitives shared by the drawing families."""

from __future__ import annotations

import html
import math
from pathlib import Path

from check_offline import check_text

from kitlib.ids import parse_ref

ASSETS = Path(__file__).resolve().parent.parent / "assets"


class ParagraphRequired(ValueError):
    """The supplied distinction is better expressed in prose."""


def esc(value):
    return html.escape(str(value), quote=True)


def label(value, maximum=48):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"text must contain 1..{maximum} characters")
    if "<" in value or any(ord(c) < 32 for c in value) or check_text(value):
        raise ValueError("labels must be plain offline text without markup or controls")
    return value


def number(value, key, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    if (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f"{key} is outside its permitted range {low}..{high}")
    return value


def refs(node):
    values = node.get("spec_ids", [])
    if (
        not isinstance(values, list)
        or len(values) > 3
        or any(not isinstance(value, str) or not parse_ref(value) for value in values)
    ):
        raise ValueError("spec_ids must contain up to three valid spec references")
    if len(" · ".join(values)) > 36:
        raise ValueError("split spec IDs across nodes: chip exceeds 36 characters")
    return values


def text(x, y, value, cls="", anchor="start"):
    return f'<text x="{x:g}" y="{y:g}" class="{cls}" text-anchor="{anchor}">{esc(value)}</text>'


def rect(x, y, w, h, cls="box", radius=8):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius}" class="{cls}"/>'


def line(x, y, xx, yy, cls="rule"):
    return f'<line x1="{x:g}" y1="{y:g}" x2="{xx:g}" y2="{yy:g}" class="{cls}"/>'


def circle(x, y, r, cls="solid"):
    return f'<circle cx="{x:g}" cy="{y:g}" r="{r:g}" class="{cls}"/>'


def path(d, cls="edge", extra=""):
    return f'<path d="{d}" class="{cls}" {extra}/>'


def polygon(points, cls="box"):
    coords = " ".join(f"{x:g},{y:g}" for x, y in points)
    return f'<polygon points="{coords}" class="{cls}"/>'


def group(node, content):
    ids = esc(" ".join(refs(node)))
    return (
        f'<g class="node" id="node-{node["id"]}" data-node="{node["id"]}" '
        f'data-spec="{ids}" data-spec-ids="{ids}">{content}</g>'
    )


def card(node, box, detail=(), focal=False):
    x, y, w, h = box
    content = rect(x, y, w, h, "box focal" if focal else "box")
    content += text(x + 16, y + 28, node["label"], "node-name")
    for i, row in enumerate(detail):
        content += text(x + 16, y + 54 + i * 24, row, "small")
    if refs(node):
        content += rect(x + 12, y + h - 38, w - 24, 28, "chip", 4)
        content += text(x + 20, y + h - 18, " · ".join(refs(node)), "ids")
    return group(node, content)


def quote_mermaid(value):
    return "".join(c if c.isalnum() or c == " " else f"#{ord(c)};" for c in str(value))
