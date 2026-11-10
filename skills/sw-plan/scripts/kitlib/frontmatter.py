"""Split, parse and rewrite the YAML front matter at the top of Markdown files."""

from __future__ import annotations

from dataclasses import dataclass
from kitlib import miniyaml
from typing import Any

_FENCE = "---"


class FrontMatterError(ValueError):
    """Front matter exists but cannot be parsed."""


@dataclass
class Parsed:
    fm: dict[str, Any] | None
    body: str
    error: str | None
    body_line: int  # 1-based file line on which body starts


def _find_block(text: str) -> tuple[str | None, str, int]:
    text = text.lstrip("\ufeff")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FENCE:
        return None, text, 1
    for index in range(1, len(lines)):
        if lines[index].strip() in (_FENCE, "..."):
            return "".join(lines[1:index]), "".join(lines[index + 1:]), index + 2
    return None, text, 1


def parse(text: str) -> Parsed:
    """Never raises; a malformed block is reported through the error field."""
    block, body, body_line = _find_block(text)
    if block is None:
        starts_fence = text.lstrip("\ufeff").startswith(_FENCE)
        error = "front matter is not closed" if starts_fence else None
        return Parsed(None, text, error, 1)
    try:
        return Parsed(miniyaml.loads(block), body, None, body_line)
    except miniyaml.YamlError as exc:
        return Parsed(None, body, f"front matter: {exc}", body_line)


def split(text: str) -> tuple[dict[str, Any] | None, str]:
    """Return (front matter or None, body); raise FrontMatterError when it is malformed."""
    parsed = parse(text)
    if parsed.error:
        raise FrontMatterError(parsed.error)
    return parsed.fm, parsed.body


def render(fm: dict[str, Any], body: str) -> str:
    return f"{_FENCE}\n{miniyaml.dumps(fm)}{_FENCE}\n{body}"


def update(text: str, changes: dict[str, Any]) -> str:
    """Set keys in the front matter and keep the body untouched.

    Key order is preserved and new keys are appended. Comments inside the block are not kept.
    """
    fm, body = split(text)
    if fm is None:
        raise FrontMatterError("no front matter to update")
    merged = dict(fm)
    merged.update(changes)
    return render(merged, body)
