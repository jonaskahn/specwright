#!/usr/bin/env python3
"""Shrink shipped HTML and CSS without changing how they render or how they are edited.

Packaging applies this to the copy it ships; the source files stay readable. The pass is
deliberately conservative:

- ``<style>`` blocks are minified as CSS (comments, indentation and spacing around
  ``{ } ; ,`` and after ``:``). Strings and ``url(...)`` are kept byte for byte, and the
  operators inside ``calc()`` keep their spaces.
- ``<pre>``, ``<textarea>`` and ``<script>`` blocks are left untouched.
- Everywhere else HTML comments, line indentation, trailing blanks and empty lines go.
  Markup keeps one element per line, so a hand-edited template page is still editable.

Usage: minify.py <file.html|file.css>...   rewrites the files in place.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAW_BLOCKS = re.compile(r"(<(pre|textarea|script)\b.*?</\2\s*>)", re.S | re.I)
STYLE_BLOCK = re.compile(r"(<style\b[^>]*>)(.*?)(</style\s*>)", re.S | re.I)
HTML_COMMENT = re.compile(r"<!--(?!\[if).*?-->", re.S)
CSS_TOKEN = re.compile(
    r"""(?P<comment>/\*.*?\*/)
      | (?P<keep>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|url\(\s*[^)'"]*\s*\))
      | (?P<space>\s+)
      | (?P<other>.)""",
    re.S | re.X,
)
# A space next to these never changes meaning. Operators such as the + and - inside
# calc() are not listed, so their required spaces survive.
TIGHT_AFTER = {"{", "}", ";", ",", ":"}
TIGHT_BEFORE = {"{", "}", ";", ","}


def minify_css(css: str) -> str:
    """Drop comments and redundant spacing; keep strings, urls and calc operators."""
    out: list[str] = []
    for match in CSS_TOKEN.finditer(css):
        kind, text = match.lastgroup, match.group()
        if kind == "comment":
            continue
        if kind == "space":
            if out and out[-1] not in TIGHT_AFTER and out[-1] != " ":
                out.append(" ")
            continue
        if kind == "other" and text in TIGHT_BEFORE:
            if out and out[-1] == " ":
                out.pop()
            if text == "}" and out and out[-1] == ";":
                out.pop()
        out.append(text)
    return "".join(out).strip()


def _strip_lines(text: str) -> str:
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def minify_html(text: str) -> str:
    """Minify embedded CSS and strip comments, indentation and blank lines."""
    parts: list[str] = []
    cursor = 0
    for raw in RAW_BLOCKS.finditer(text):
        parts.append(_minify_markup(text[cursor : raw.start()]))
        parts.append(raw.group(1))
        cursor = raw.end()
    parts.append(_minify_markup(text[cursor:]))
    return "".join(parts)


def _edge(space: str) -> str:
    """Whitespace at a segment edge collapses to one newline or space, never to nothing."""
    return "\n" if "\n" in space else (" " if space else "")


def _minify_markup(text: str) -> str:
    if not text.strip():
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()) :]
    pieces: list[str] = []
    cursor = 0
    for style in STYLE_BLOCK.finditer(text):
        pieces.append(_strip_lines(HTML_COMMENT.sub("", text[cursor : style.start()])))
        pieces.append(style.group(1) + minify_css(style.group(2)) + style.group(3))
        cursor = style.end()
    pieces.append(_strip_lines(HTML_COMMENT.sub("", text[cursor:])))
    return _edge(lead) + "\n".join(p for p in pieces if p) + _edge(trail)


def minify_file(path: Path) -> None:
    if path.suffix not in (".css", ".html"):
        return  # binary assets such as the packed console stay as they are
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".css":
        result = minify_css(text) + "\n"
    elif path.suffix == ".html":
        result = minify_html(text)
    else:
        return
    if result != text:
        path.write_text(result, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    paths = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not paths:
        print(__doc__, file=sys.stderr)
        return 2
    for path in paths:
        minify_file(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
