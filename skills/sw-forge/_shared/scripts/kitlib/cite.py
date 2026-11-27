"""Durable citations: `SRC-0001:L12-L14#a1b2`.

The line numbers count lines of the saved snapshot file, so `sed -n 12p` finds the line. The
optional four-hex suffix is a hash of the quoted text. It lets a check tell a moved or edited
line from a correct one, and lets a re-import be compared line by line. Nothing here rewrites
an accepted record.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from kitlib import frontmatter, ids

CITATION = re.compile(
    r"(?<![\w-])(?:([A-Z]{2,5}):)?(SRC-\d{4}):L(\d+)(?:-L?(\d+))?(?:#([0-9a-f]{4}))?\b"
)
SKIP_PARTS = {"00-inbox", "raw", "graph", ".git", "node_modules"}


@dataclass(frozen=True)
class Citation:
    scope: str | None
    source: str
    start: int
    end: int
    digest: str
    line: int  # where the citation was found in the citing text

    def text(self) -> str:
        span = f"L{self.start}" if self.end == self.start else f"L{self.start}-L{self.end}"
        return f"{self.source}:{span}" + (f"#{self.digest}" if self.digest else "")


@dataclass(frozen=True)
class Problem:
    line: int
    code: str
    message: str
    severity: str  # "error" blocks; "warn" is weak evidence


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def quote_hash(lines: list[str]) -> str:
    """Four hex characters over the normalized quoted lines."""
    joined = "\n".join(normalize(line) for line in lines)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:4]


def find(text: str) -> list[Citation]:
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        for m in CITATION.finditer(line):
            start = int(m.group(3))
            end = int(m.group(4) or start)
            found.append(Citation(m.group(1), m.group(2), start, end, m.group(5) or "", number))
    return found


class Sources:
    """Snapshots of one scope, read once and only when a citation names them."""

    def __init__(self, base: Path) -> None:
        self.base = base
        self._lines: dict[str, list[str] | None] = {}
        self._fm: dict[str, dict] = {}
        self._superseded: set[str] | None = None

    def lines(self, source: str) -> list[str] | None:
        if source not in self._lines:
            path = ids.find_record(self.base / "00-inbox", source)
            if path is None or path.is_symlink():
                self._lines[source] = None
            else:
                text = path.read_text(encoding="utf-8")
                self._lines[source] = text.splitlines()
                self._fm[source] = frontmatter.parse(text).fm or {}
        return self._lines[source]

    def header(self, source: str) -> dict:
        self.lines(source)
        return self._fm.get(source, {})

    def superseded(self) -> set[str]:
        if self._superseded is None:
            found: set[str] = set()
            for path in sorted((self.base / "00-inbox").glob("SRC-*.md")):
                fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
                value = fm.get("supersedes") or []
                found.update(r.id for r in ids.find_refs(str(value)))
            self._superseded = found
        return self._superseded


def problems(sources: Sources, text: str, require_hash: bool = False) -> list[Problem]:
    out: list[Problem] = []
    for c in find(text):
        lines = sources.lines(c.source)
        if lines is None:
            out.append(
                Problem(c.line, "missing-source", f"{c.text()}: no snapshot {c.source}", "error")
            )
            continue
        if c.start < 1 or c.end < c.start or c.end > len(lines):
            out.append(
                Problem(
                    c.line,
                    "line-out-of-range",
                    f"{c.text()}: {c.source} has {len(lines)} lines",
                    "error",
                )
            )
            continue
        quoted = lines[c.start - 1 : c.end]
        if not any(line.strip() for line in quoted):
            out.append(Problem(c.line, "blank-line", f"{c.text()}: cited lines are blank", "error"))
            continue
        if c.digest and quote_hash(quoted) != c.digest:
            out.append(
                Problem(
                    c.line,
                    "hash-mismatch",
                    f"{c.text()}: text changed; now #{quote_hash(quoted)}",
                    "error",
                )
            )
        elif require_hash and not c.digest:
            out.append(
                Problem(c.line, "no-hash", f"{c.text()}: add #{quote_hash(quoted)}", "error")
            )
        if c.source in sources.superseded():
            out.append(
                Problem(c.line, "superseded-source", f"{c.text()}: source was superseded", "warn")
            )
        if sources.header(c.source).get("content_class") in ("index-only", "empty"):
            out.append(
                Problem(
                    c.line,
                    "weak-source",
                    f"{c.text()}: source is an index-only page, not settled evidence",
                    "warn",
                )
            )
    return out


def documents(target: Path) -> list[Path]:
    """Markdown files to check; snapshots, raw files and generated graph output are skipped."""
    if target.is_file():
        return [target]
    return [
        p
        for p in sorted(target.rglob("*.md"))
        if not SKIP_PARTS & set(p.relative_to(target).parts) and not p.is_symlink()
    ]


def verify(base: Path, target: Path, require_hash: bool = False) -> list[tuple[str, Problem]]:
    sources = Sources(base)
    found = []
    for path in documents(target):
        rel = path.relative_to(base).as_posix() if path.is_relative_to(base) else str(path)
        for problem in problems(sources, path.read_text(encoding="utf-8"), require_hash):
            found.append((rel, problem))
    return found


def parse_one(text: str) -> Citation:
    cites = find(text.strip())
    if len(cites) != 1:
        raise ValueError(f"not a citation: {text}")
    return cites[0]


def quote(sources: Sources, citation: Citation) -> str:
    """Exact cited text, copied by program."""
    lines = sources.lines(citation.source)
    if lines is None:
        raise ValueError(f"no snapshot {citation.source}")
    if citation.start < 1 or citation.end > len(lines) or citation.end < citation.start:
        raise ValueError(f"{citation.text()}: {citation.source} has {len(lines)} lines")
    return "\n".join(lines[citation.start - 1 : citation.end])


def stamp(sources: Sources, citation: Citation) -> str:
    """The citation with its hash filled in from the saved text."""
    body = quote(sources, citation).splitlines()
    span = (
        f"L{citation.start}"
        if citation.end == citation.start
        else f"L{citation.start}-L{citation.end}"
    )
    return f"{citation.source}:{span}#{quote_hash(body)}"


def rebase(
    old: Sources, new: Sources, old_id: str, new_id: str, citing: list[tuple[str, Citation]]
) -> list[tuple[str, int, str, str, str]]:
    """Proposed `(file, line, old citation, new citation, note)` rows; nothing is written."""
    new_lines = new.lines(new_id) or []
    rows = []
    for rel, c in citing:
        if c.source != old_id:
            continue
        try:
            wanted = [normalize(x) for x in quote(old, c).splitlines()]
        except ValueError as exc:
            rows.append((rel, c.line, c.text(), "", str(exc)))
            continue
        width = len(wanted)
        hits = [
            i + 1
            for i in range(len(new_lines) - width + 1)
            if [normalize(x) for x in new_lines[i : i + width]] == wanted
        ]
        if len(hits) == 1:
            start = hits[0]
            end = start + width - 1
            proposed = stamp(new, Citation(None, new_id, start, end, "", c.line))
            rows.append((rel, c.line, c.text(), proposed, "unchanged text found"))
        else:
            note = "text not found in the new source" if not hits else "text appears several times"
            rows.append((rel, c.line, c.text(), "", note))
    return rows
