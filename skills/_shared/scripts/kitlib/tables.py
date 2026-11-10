"""Read and write one Markdown table inside a larger document without disturbing the rest."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EMPTY = "—"
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$")


class TableError(ValueError):
    pass


def split_row(line: str) -> list[str]:
    """Split a table row at unescaped pipes."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells = re.split(r"(?<!\\)\|", text)
    return [cell.strip().replace("\\|", "|") for cell in cells]


def _join(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]] = field(default_factory=list)

    def col(self, name: str) -> int:
        try:
            return self.header.index(name)
        except ValueError:
            raise TableError(f"no column '{name}'; columns are {self.header}") from None

    def find(self, key: str) -> list[str] | None:
        """Row whose first cell equals key."""
        for row in self.rows:
            if row[0] == key:
                return row
        return None

    def get(self, key: str, column: str) -> str | None:
        row = self.find(key)
        return row[self.col(column)] if row else None

    def upsert(self, key: str, cells: dict[str, str] | None = None) -> bool:
        """Create the row if missing and set the given cells; return True when it was created."""
        row = self.find(key)
        created = row is None
        if row is None:
            row = [key] + [EMPTY] * (len(self.header) - 1)
            self.rows.append(row)
        for name, value in (cells or {}).items():
            index = self.col(name)
            if index == 0:
                raise TableError("the key column cannot be changed")
            row[index] = value if value != "" else EMPTY
        return created

    def render(self) -> str:
        lines = [_join(self.header), "|" + "|".join("---" for _ in self.header) + "|"]
        lines += [_join(row) for row in self.rows]
        return "\n".join(lines) + "\n"


@dataclass
class Document:
    before: str
    table: Table | None
    after: str

    def render(self) -> str:
        if self.table is None:
            return self.before
        return self.before + self.table.render() + self.after


def parse(text: str) -> Document:
    """Find the first table. Text before and after it is kept byte for byte."""
    lines = text.splitlines(keepends=True)
    start = next(
        (
            i
            for i in range(len(lines) - 1)
            if lines[i].lstrip().startswith("|") and _SEPARATOR.match(lines[i + 1])
        ),
        None,
    )
    if start is None:
        return Document(text, None, "")
    header = split_row(lines[start])
    end = start + 2
    rows: list[list[str]] = []
    while end < len(lines) and lines[end].lstrip().startswith("|"):
        cells = split_row(lines[end])
        if len(cells) > len(header):
            raise TableError(f"row {end + 1} has {len(cells)} cells, header has {len(header)}")
        rows.append(cells + [EMPTY] * (len(header) - len(cells)))
        end += 1
    return Document("".join(lines[:start]), Table(header, rows), "".join(lines[end:]))
