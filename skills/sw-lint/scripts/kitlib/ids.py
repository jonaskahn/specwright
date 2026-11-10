"""ID grammar, qualified references and allocation that never reuses a number."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

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
}

_ID = r"(?:FEAT|BO|BR|STK|DEC|Q|CR|RISK)-\d{3}|SRC-\d{4}|N?FR-[A-Z]{2,5}-\d{3}|AC-\d{3}-\d+"
_REF = re.compile(rf"\b(?:([A-Z]{{2,5}}):)?({_ID})\b")
_REF_FULL = re.compile(rf"^(?:([A-Z]{{2,5}}):)?({_ID})$")
_AC = re.compile(r"^AC-(\d{3})-(\d+)$")
_TOMBSTONE = re.compile(r"~~(AC-\d{3}-\d+)~~")
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
