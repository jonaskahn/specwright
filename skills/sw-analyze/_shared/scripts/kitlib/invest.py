"""The INVEST table of an idea brief in a fixed, machine-readable shape.

Under `## Proposed FEAT split` (or `## INVEST`) a brief holds one table:

    | Feature | I | N | V | E | S | T | Reason |

Each letter cell is `pass`, `fail` or `unknown`. A row with any `fail` or `unknown` explains why
in Reason. The board totals the cells per brief and per letter, so an unknown is never counted as
a pass.
"""

from __future__ import annotations

from pathlib import Path

from kitlib import frontmatter, markdown, tables

LETTERS = ("I", "N", "V", "E", "S", "T")
VALUES = ("pass", "fail", "unknown")
HEADER = ["Feature", *LETTERS, "Reason"]
SECTION_NAMES = ("proposed feat split", "invest")


def _table(body: str) -> tables.Table | None:
    for section in markdown.iter_sections(body):
        if section.name.casefold() in SECTION_NAMES:
            doc = tables.parse(section.text)
            if doc.table is not None:
                return doc.table
    return None


def has_section(body: str) -> bool:
    return any(s.name.casefold() in SECTION_NAMES for s in markdown.iter_sections(body))


def parse(body: str) -> tuple[list[dict[str, str]], list[str]]:
    """Rows as dicts, and every way the table departs from the format."""
    table = _table(body)
    if table is None:
        return [], ["no INVEST table under Proposed FEAT split"]
    if table.header != HEADER:
        return [], [f"INVEST table columns must be {' | '.join(HEADER)}"]
    rows: list[dict[str, str]] = []
    problems: list[str] = []
    for raw in table.rows:
        row = dict(zip(HEADER, (c.strip() for c in raw), strict=True))
        label = row["Feature"] or "(unnamed row)"
        if not row["Feature"] or row["Feature"] == tables.EMPTY:
            problems.append("a row has no Feature")
        for letter in LETTERS:
            value = row[letter].casefold()
            if value not in VALUES:
                problems.append(
                    f"{label}: {letter} must be pass, fail or unknown, not '{row[letter]}'"
                )
            row[letter] = value
        weak = any(row[letter] != "pass" for letter in LETTERS)
        if weak and row["Reason"] in ("", tables.EMPTY):
            problems.append(f"{label}: a fail or unknown needs a Reason")
        rows.append(row)
    return rows, problems


def problems(body: str) -> list[str]:
    """Format problems; empty when the brief has no INVEST section yet."""
    return parse(body)[1] if has_section(body) else []


def totals(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    """`{letter: {pass, fail, unknown}}` over all rows."""
    out = {letter: {v: 0 for v in VALUES} for letter in LETTERS}
    for row in rows:
        for letter in LETTERS:
            if row[letter] in VALUES:
                out[letter][row[letter]] += 1
    return out


def row_summary(row: dict[str, str]) -> dict[str, int]:
    """Cells of one feature by outcome; the readiness ranking uses `fail` and `unknown`."""
    cells = [row[letter] for letter in LETTERS]
    return {v: cells.count(v) for v in VALUES}


def board(base: Path) -> list[dict]:
    """Per idea brief: its id, row count, totals per letter and format problems."""
    found = []
    for path in sorted((base / "01-analysis/ideas").glob("*.md")):
        parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
        if not has_section(parsed.body):
            continue
        rows, bad = parse(parsed.body)
        found.append(
            {
                "idea": str((parsed.fm or {}).get("id", path.stem)),
                "title": str((parsed.fm or {}).get("title", "")),
                "rows": len(rows),
                "totals": totals(rows),
                "problems": bad,
            }
        )
    return found
