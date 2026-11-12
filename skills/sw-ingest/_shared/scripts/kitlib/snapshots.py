"""Facts about a converted snapshot that later steps need: its page class and its redactions."""

from __future__ import annotations

import re

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_LINK_ONLY = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?(?:\[[^\]]*\]\([^)]*\)|<?https?://\S+>?)\s*$")
_MACRO = re.compile(
    r"^\s*(?:\{\{?\s*(?:toc|children|child[- ]pages?|index)[^}]*\}?\}|\[TOC\])\s*$", re.I
)
_RULE = re.compile(r"^\s*(?:[-*_]{3,}|\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)*\|?)\s*$")
_WORD = re.compile(r"[^\W\d_]{2,}", re.U)
PROSE_WORDS = 20


def content_class(text: str) -> str:
    """`empty`, `index-only` or `content`.

    An index-only page is headings, link lists and navigation macros with almost no prose. It tells
    a reader where things are but settles nothing, so later steps must not cite it as evidence.
    """
    structural = 0
    prose: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.strip().startswith(">") and not line.strip("> "):
            continue
        if (
            _HEADING.match(line)
            or _LINK_ONLY.match(line)
            or _MACRO.match(line)
            or _RULE.match(line)
        ):
            structural += 1
            continue
        prose.append(re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line))
    words = sum(len(_WORD.findall(line)) for line in prose)
    if not structural and not words:
        return "empty"
    if words < PROSE_WORDS and structural:
        return "index-only"
    if not words:
        return "empty"
    return "content"


def redaction_markers(text: str) -> int:
    return text.count("[REDACTED:")
