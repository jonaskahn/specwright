"""Existing-baseline helpers: normalize a legacy register, group it and draft one brief per group.

A project that already runs many capabilities under its own IDs starts from a register of them.
The register becomes `01-analysis/baseline/register.tsv`; every legacy ID is kept as an alias of the
feature that stands for it, so the business's own name always finds the record.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from kitlib import frontmatter, ids

REGISTER = "01-analysis/baseline/register.tsv"
PROPOSAL = "01-analysis/baseline/split-proposal.tsv"
COLUMNS = ("legacy_id", "title", "group", "source_ref")
SYNONYMS = {
    "legacy_id": ("legacy_id", "legacy id", "id", "key", "code"),
    "title": ("title", "name", "summary", "feature"),
    "group": ("group", "epic", "module", "area", "category"),
    "source_ref": ("source_ref", "source ref", "page_id", "page id", "page", "source", "url"),
}


class BaselineError(ValueError):
    pass


def _cell(value: object) -> str:
    return re.sub(r"[\t\r\n]+", " ", str(value or "")).strip()


def parse_register(text: str, pattern: str = "") -> list[dict[str, str]]:
    """Rows of a comma- or tab-separated legacy register, with names normalized and checked."""
    first = next((ln for ln in text.splitlines() if ln.strip()), "")
    delimiter = "\t" if "\t" in first else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [r for r in reader if any(c.strip() for c in r) and not r[0].startswith("#")]
    if len(rows) < 2:
        raise BaselineError("the register needs a header row and at least one item")
    header = [h.strip().casefold() for h in rows[0]]
    index: dict[str, int] = {}
    for name, options in SYNONYMS.items():
        found = next((header.index(o) for o in options if o in header), None)
        if found is not None:
            index[name] = found
    for needed in ("legacy_id", "title"):
        if needed not in index:
            raise BaselineError(f"the register needs a '{needed}' column")
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    regex = re.compile(pattern) if pattern else None
    for number, raw in enumerate(rows[1:], 2):
        row = {
            name: _cell(raw[index[name]]) if name in index and index[name] < len(raw) else ""
            for name in COLUMNS
        }
        if not row["legacy_id"] or not row["title"]:
            raise BaselineError(f"row {number}: legacy_id and title are required")
        if regex and not regex.fullmatch(row["legacy_id"]):
            raise BaselineError(f"row {number}: '{row['legacy_id']}' does not match {pattern}")
        key = row["legacy_id"].casefold()
        if key in seen:
            raise BaselineError(f"row {number}: legacy_id '{row['legacy_id']}' appears twice")
        seen.add(key)
        out.append(row)
    return out


def render_register(rows: list[dict[str, str]]) -> str:
    lines = ["\t".join(COLUMNS)]
    lines += ["\t".join(_cell(r.get(c, "")) for c in COLUMNS) for r in rows]
    return "\n".join(lines) + "\n"


def groups(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        out.setdefault(row.get("group") or "ungrouped", []).append(row)
    return dict(sorted(out.items()))


def proposal_text(grouped: dict[str, list[dict[str, str]]], mapped: set[str]) -> str:
    """One line per legacy item still without a feature: `group  legacy_id  title`."""
    lines = ["# group\tlegacy_id\ttitle"]
    for group, rows in grouped.items():
        lines += [
            f"{_cell(group)}\t{_cell(r['legacy_id'])}\t{_cell(r['title'])}"
            for r in rows
            if r["legacy_id"].casefold() not in mapped
        ]
    return "\n".join(lines) + "\n"


def item_arg(row: dict[str, str]) -> str:
    """`Title|LEG-100`, the form `record.py reserve feat --item` takes."""
    return f"{row['title']}|{row['legacy_id']}"


def sources_for(base: Path, rows: list[dict[str, str]]) -> list[str]:
    """Snapshots whose remote ID or aliases match a row's source reference or legacy ID."""
    wanted = {r["source_ref"].casefold() for r in rows if r.get("source_ref")}
    wanted |= {r["legacy_id"].casefold() for r in rows}
    found = []
    for path in sorted((base / "00-inbox").glob("SRC-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        names = {str(a).casefold() for a in fm.get("aliases") or []}
        names.add(str(fm.get("remote_id", "")).casefold())
        if names & wanted:
            found.append(str(fm["id"]))
    return found


def brief_text(
    scope: str, group: str, rows: list[dict[str, str]], features: dict[str, str], sources: list[str]
) -> tuple[str, str]:
    """`(idea id, file text)` for one group; the writing itself is left to a person."""
    slug = ids.slugify(group) or "ungrouped"
    identity = f"IDEA-baseline-{slug}"
    fm = {
        "id": identity,
        "type": "idea",
        "scope": scope,
        "title": f"Baseline: {group}",
        "aliases": [],
        "status": "draft",
        "home": "repo",
        "sources": sources,
    }
    split = [
        "| Feature | I | N | V | E | S | T | Reason |",
        "|---|---|---|---|---|---|---|---|",
    ]
    legacy = ["| Legacy ID | Feature | Title | Source |", "|---|---|---|---|"]
    for r in rows:
        key = features.get(r["legacy_id"].casefold(), "")
        split.append(
            f"| {r['title']} ({r['legacy_id']}) | "
            + " | ".join(["unknown"] * 6)
            + " | Not yet assessed |"
        )
        legacy.append(
            f"| {r['legacy_id']} | {key or '—'} | {r['title']} | {r.get('source_ref') or '—'} |"
        )
    body = f"""## Frame

The business already runs {len(rows)} capabilities in the group "{group}".
Name the actor, context and needed result from the cited sources.

## Actors

Not yet written. Cite the sources.

## Problem

Not yet written. State the obstacle each capability removes, from the sources,
without naming a design.

## Smallest valuable outcome

Not yet written. State the observable improvement for the actor,
without prescribing a design.

## Non-goals

- Not yet written — reason: record it with the PO.
- Not yet written — reason: record it with the PO.
- Not yet written — reason: record it with the PO.

## Ranked questions

The first question is already recorded: keep each legacy item as one feature, or re-split by INVEST.

## Assumptions

Not yet written.

## Risks

Not yet written.

## Proposed FEAT split

Each legacy item stands for one feature until the split decision says otherwise.
Replace `unknown` only with evidence.

{chr(10).join(split)}

## Legacy items

{chr(10).join(legacy)}

## Design-leakage self-check

Run the leakage scan on Problem and Smallest valuable outcome once they are written.
"""
    return identity, frontmatter.render(fm, body)
