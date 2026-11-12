"""Find one-sided CSS borders, which the kit forbids in anything it generates.

A declaration block is flagged when it sets a border on a single side (or logical side) to a
visible value and has no full `border` shorthand next to it. Rendering differs across themes
for lone edge borders, so full borders, outlines, tints or box-shadow are used instead.
"""

from __future__ import annotations

import re

ONE_SIDED = re.compile(
    r"(?<![\w-])border-(?:left|right|top|bottom|inline-start|inline-end|inline|block-start"
    r"|block-end|block)\s*:\s*(?!\s)(?!none\b|0\b|0px\b)[^;}\"']+",
    re.I,
)
FULL = re.compile(r"(?<![\w-])border\s*:\s*(?!\s)(?!none\b|0\b|0px\b)[^;}\"']+", re.I)
_BLOCK = re.compile(r"\{([^{}]*)\}")
_STYLE_ATTR = re.compile(r"style\s*=\s*(\"[^\"]*\"|'[^']*')", re.I)

HINT = "use a full border, an outline, a background tint or box-shadow"


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def find_one_sided(text: str) -> list[tuple[int, str]]:
    """Return (line, message) for every declaration block with a lone one-sided border."""
    spans = [(m.start(1), m.group(1)) for m in _BLOCK.finditer(text)]
    spans += [(m.start(1) + 1, m.group(1)[1:-1]) for m in _STYLE_ATTR.finditer(text)]
    found: list[tuple[int, str]] = []
    for start, decl in spans:
        if FULL.search(decl):
            continue
        for match in ONE_SIDED.finditer(decl):
            side = match.group(0).split(":")[0].strip()
            found.append((_line_of(text, start + match.start()), f"one-sided {side} ({HINT})"))
    return sorted(set(found))
