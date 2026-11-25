"""ID grammar, qualified references and allocation that never reuses a number."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

TYPE_PATTERNS = {
    "feature": r"FEAT-\d{3}",
    "bo": r"BO-\d{3}",
    "br": r"BR-\d{3}",
    "stk": r"STK-\d{3}",
    "fr": r"FR-[A-Z]{2,5}-\d{3}",
    "nfr": r"NFR-[A-Z]{2,5}-\d{3}",
    "src": r"SRC-\d{4}",
    "snapshot": r"SRC-\d{4}",
    "dec": r"DEC-\d{3}",
    "q": r"Q-\d{3}",
    "cr": r"CR-\d{3}",
    "risk": r"RISK-\d{3}",
    "idea": r"IDEA-[a-z0-9-]+",
    "epic": r"EPIC-\d{3}",
    "task": r"TASK-\d{3}-\d+",
    "asset": r"ASSET-\d{3}",
    "amendment": r"AMD-\d{3}",
    "candidates": r"CAND-\d{3}",
}

_ID = (
    r"(?:FEAT|BO|BR|STK|DEC|Q|CR|RISK|EPIC|AMD|CAND)-\d{3}|SRC-\d{4}|N?FR-[A-Z]{2,5}-\d{3}"
    r"|AC-\d{3}-\d+|TASK-\d{3}-\d+|ASSET-\d{3}"
)
_REF = re.compile(rf"\b(?:([A-Z]{{2,5}}):)?({_ID})\b")
_REF_FULL = re.compile(rf"^(?:([A-Z]{{2,5}}):)?({_ID})$")
_AC = re.compile(r"^AC-(\d{3})-(\d+)$")
_TASK = re.compile(r"^TASK-(\d{3})-(\d+)$")
_TOMBSTONE = re.compile(r"~~(AC-\d{3}-\d+)~~")
_TASK_TOMBSTONE = re.compile(r"~~(TASK-\d{3}-\d+)~~")
_STORY = re.compile(r"^(?:([A-Z]{2,5}):)?STORY-(\d{3})$")
_SCOPE = re.compile(r"^[A-Z]{2,5}$")


@dataclass(frozen=True)
class Ref:
    scope: str | None
    id: str

    @property
    def qualified(self) -> str:
        return f"{self.scope}:{self.id}" if self.scope else self.id

    def __str__(self) -> str:
        return self.qualified


def is_scope(value: str) -> bool:
    return bool(_SCOPE.match(value))


def parse_ref(text: str) -> Ref | None:
    """Parse 'BR-001' or 'REF:BR-001'; return None for anything else."""
    match = _REF_FULL.match(text.strip())
    return Ref(match.group(1), match.group(2)) if match else None


def find_refs(text: str) -> list[Ref]:
    """All distinct references in a text, in order of first appearance."""
    seen: dict[Ref, None] = {}
    for match in _REF.finditer(text):
        seen.setdefault(Ref(match.group(1), match.group(2)), None)
    return list(seen)


def matches_type(doc_type: str, spec_id: str) -> bool:
    pattern = TYPE_PATTERNS.get(doc_type)
    return bool(pattern and re.fullmatch(pattern, spec_id))


def prefix_of(spec_id: str) -> str:
    """Return 'FEAT' for FEAT-001, 'NFR' for NFR-REF-001, 'AC' for AC-001-2."""
    return spec_id.split("-", 1)[0]


def qualify(scope: str, spec_id: str) -> str:
    return f"{scope}:{spec_id}"


def feat_number(feat_id: str) -> int:
    match = re.fullmatch(r"FEAT-(\d{3})", feat_id)
    if not match:
        raise ValueError(f"not a feature id: {feat_id}")
    return int(match.group(1))


def ac_id(feat_no: int, n: int) -> str:
    return f"AC-{feat_no:03d}-{n}"


def parse_ac(spec_id: str) -> tuple[int, int] | None:
    """Return (feature number, criterion number) for an AC id."""
    match = _AC.match(spec_id)
    return (int(match.group(1)), int(match.group(2))) if match else None


def tombstones(text: str) -> list[str]:
    """Withdrawn criteria kept as '~~AC-001-3~~' so their numbers are never reused."""
    return _TOMBSTONE.findall(text)


def task_id(feat_no: int, n: int) -> str:
    return f"TASK-{feat_no:03d}-{n}"


def parse_task(spec_id: str) -> tuple[int, int] | None:
    """Return (feature number, task number) for a task id."""
    match = _TASK.match(spec_id)
    return (int(match.group(1)), int(match.group(2))) if match else None


def task_tombstones(text: str) -> list[str]:
    """Withdrawn tasks kept as '~~TASK-001-3~~' so their numbers are never reused."""
    return _TASK_TOMBSTONE.findall(text)


def story_alias(text: str) -> str:
    """Map the BA/PO word STORY-001 to the canonical FEAT-001; other text is unchanged.

    STORY is an input alias only. No STORY id is ever written to an artifact.
    """
    match = _STORY.match(text.strip())
    if not match:
        return text
    prefix = f"{match.group(1)}:" if match.group(1) else ""
    return f"{prefix}FEAT-{match.group(2)}"


def next_id(prefix: str, taken: Iterable[str], width: int = 3) -> str:
    """Next free id for a prefix such as 'BR' or 'NFR-REF'.

    Pass every id ever used, including withdrawn ones, so numbers are not reused.
    """
    pattern = re.compile(rf"^(?:[A-Z]{{2,5}}:)?{re.escape(prefix)}-(\d+)$")
    highest = 0
    for item in taken:
        match = pattern.match(item)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}-{highest + 1:0{width}d}"


_NAME_ID = re.compile(rf"^(?:{_ID})(?=--|\.|$)")
SLUG_MAX = 48


def slugify(title: str, limit: int = SLUG_MAX) -> str:
    """Lowercase ASCII words joined by hyphens, cut at a word boundary; may be empty."""
    plain = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    words = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")
    if len(words) <= limit:
        return words
    return words[:limit].rsplit("-", 1)[0] if "-" in words[:limit] else words[:limit]


def record_filename(identity: str, title: str, suffix: str = ".md") -> str:
    """`<ID>--<slug>.md`. The ID is the stable part; the slug may change without breaking links."""
    slug = slugify(title)
    return f"{identity}--{slug}{suffix}" if slug else f"{identity}{suffix}"


def id_from_name(name: str) -> str | None:
    """The ID leading a file name or stem: `Q-001`, `Q-001--slug.md` or `FEAT-001.story.md`."""
    match = _NAME_ID.match(Path(name).name)
    return match.group(0) if match else None


def find_record(folder: Path, identity: str) -> Path | None:
    """File holding an ID, named `<ID>.md` or `<ID>--<slug>.md`; None when absent."""
    exact = folder / f"{identity}.md"
    if exact.is_file():
        return exact
    named = sorted(folder.glob(f"{identity}--*.md")) if folder.is_dir() else []
    return named[0] if named else None


_SKIP_DIRS = {".git", "raw", "graph", "node_modules", "__pycache__"}


def taken_ids(base: Path) -> list[str]:
    """Every ID named by any file name or text under a scope, withdrawn ones included."""
    found: list[str] = []
    for path in sorted(base.rglob("*.md")):
        if _SKIP_DIRS & set(path.relative_to(base).parts) or path.is_symlink():
            continue
        found.extend(ref.id for ref in find_refs(path.name))
        found.extend(ref.id for ref in find_refs(path.read_text(encoding="utf-8")))
    return found
