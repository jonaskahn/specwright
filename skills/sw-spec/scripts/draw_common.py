"""Inert text contract shared by the drawing families: escaping, limits and IDs."""

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


def quote_mermaid(value):
    return "".join(c if c.isalnum() or c == " " else f"#{ord(c)};" for c in str(value))
