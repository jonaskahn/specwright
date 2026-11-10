"""Section and acceptance-criterion helpers shared by lint, diff and spec tooling."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{1,6}) +(.+?)\s*#*\s*$")
_AC_HEADING = re.compile(r"^### +(AC-\d{3}-\d+)\b\s*(?:[—–-]+\s*(.*))?$")
_AC_TOMBSTONE = re.compile(r"~~(AC-\d{3}-\d+)~~")


@dataclass
class Section:
    name: str
    line: int  # file line of the heading
    lines: list[tuple[int, str]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(text for _, text in self.lines).strip()


@dataclass
class AcBlock:
    id: str
    line: int
    title: str
    text: str


def iter_sections(body: str, level: int = 2, first_line: int = 1) -> list[Section]:
    """Split a body at headings of the given level; headings inside code fences are ignored."""
    sections: list[Section] = []
    fenced = False
    for number, line in enumerate(body.splitlines(), first_line):
        if _FENCE.match(line):
            fenced = not fenced
        match = None if fenced else _HEADING.match(line)
        if match and len(match.group(1)) == level:
            sections.append(Section(match.group(2).strip(), number))
        elif sections:
            sections[-1].lines.append((number, line))
    return sections


def sections(body: str, level: int = 2, first_line: int = 1) -> dict[str, Section]:
    """Map heading to section; the first section wins when a heading repeats."""
    out: dict[str, Section] = {}
    for section in iter_sections(body, level, first_line):
        out.setdefault(section.name, section)
    return out


def drop_section(body: str, name: str, level: int = 2) -> str:
    """Remove a section, heading included, from a body."""
    kept: list[str] = []
    skipping = False
    fenced = False
    for line in body.splitlines(keepends=True):
        if _FENCE.match(line):
            fenced = not fenced
        match = None if fenced else _HEADING.match(line.rstrip("\r\n"))
        if match and len(match.group(1)) == level:
            skipping = match.group(2).strip() == name
        if not skipping:
            kept.append(line)
    return "".join(kept)


def ac_blocks(section: Section | None) -> dict[str, AcBlock]:
    """Parse '### AC-001-1 — title' blocks from an acceptance criteria section."""
    blocks: dict[str, AcBlock] = {}
    current: AcBlock | None = None
    if section is None:
        return blocks
    for number, line in section.lines:
        match = _AC_HEADING.match(line)
        if match:
            current = AcBlock(match.group(1), number, (match.group(2) or "").strip(), "")
            blocks[current.id] = current
        elif current is not None:
            current.text += line + "\n"
    return blocks


def ac_tombstones(section: Section | None) -> list[str]:
    """IDs of withdrawn acceptance criteria that are kept as '~~AC-001-3~~' lines."""
    if section is None:
        return []
    return [m.group(1) for _, line in section.lines for m in _AC_TOMBSTONE.finditer(line)]


def normalise(text: str) -> str:
    """LF line endings, no trailing spaces, no surrounding blank lines."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    return "\n".join(lines).strip()
