"""Per-document record of what the sensitive-content scan decided, and who allowed an example.

One tab-separated line per decision: `source_hash line type decision by ref date`. A decision is
`retain` (clean, kept), `redact` (kept with markers), `skip` (refused) or `example` (a sample value
inside a policy text that a named person reviewed). Only `example` rows change what the scan
reports, and only for personal data, never for secrets.
"""

from __future__ import annotations

import os
from pathlib import Path

COLUMNS = ("source_hash", "line", "type", "decision", "by", "ref", "date")
DECISIONS = ("retain", "redact", "skip", "example")
HEADER = "# " + "\t".join(COLUMNS)


def _clean(value: object) -> str:
    return " ".join(str(value).replace("\t", " ").split())


def read(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) == len(COLUMNS):
            rows.append(dict(zip(COLUMNS, parts, strict=True)))
    return rows


def append(path: Path, row: dict[str, object]) -> None:
    """Append one decision; refuses a decision that names no one or no evidence."""
    if row["decision"] not in DECISIONS:
        raise ValueError(f"decision must be one of {', '.join(DECISIONS)}")
    if row["decision"] == "example" and not (
        _clean(row.get("by", "")) and _clean(row.get("ref", ""))
    ):
        raise ValueError("an example allowance needs a named reviewer and an evidence reference")
    line = "\t".join(_clean(row.get(name, "-")) or "-" for name in COLUMNS) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = not path.exists()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, ((HEADER + "\n") if fresh else "").encode("utf-8") + line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def allowed(rows: list[dict[str, str]], source_hash: str) -> frozenset[tuple[int, str]]:
    """`(line, type)` pairs a reviewer allowed as documented examples for this exact source."""
    found = set()
    for row in rows:
        named = row["by"] not in ("", "-") and row["ref"] not in ("", "-")
        wanted = row["source_hash"] == source_hash and row["decision"] == "example"
        if wanted and named and row["line"].isdigit():
            found.add((int(row["line"]), row["type"]))
    return frozenset(found)
