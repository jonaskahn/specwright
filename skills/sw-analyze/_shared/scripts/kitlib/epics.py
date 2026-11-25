"""Epic allocation shared by the shaping script and the record tools."""

from __future__ import annotations

from pathlib import Path

from kitlib import frontmatter, ids

DEFAULT_TEMPLATE = """---
id: EPIC-NNN
type: epic
scope: <SCOPE>
title: <outcome-led title>
status: draft
bo: []
scopes: [<SCOPE>]
---

## Outcome

<The business outcome this epic groups features under; no interface or technology choices.>

## Features

<FEAT references linked to this epic, or None until the PO accepts the split.>

## Projects involved

<Home project and any other project whose features join this epic, with the reason.>

## Jira

<Existing Jira key if the ID registry maps one, else None. Epics are never published.>
"""


def objectives(root: Path, scope: str, values: list[str] | None) -> list[str]:
    """Check the business objectives an epic serves and return them as written, without repeats.

    An objective of this project must exist as a card; one of another project is accepted as a
    qualified ID (ORD:BO-001) because only the graph can resolve it.
    """
    found: list[str] = []
    for value in values or []:
        for ref in ids.find_refs(value) or [None]:
            if ref is None or not ids.matches_type("bo", ref.id):
                raise ValueError(f"'{value}' is not a business objective ID such as BO-001")
            if ref.scope not in (None, scope):
                text = ref.qualified
            else:
                cards = (root / "01-analysis").rglob("*.md")
                if not any(ids.id_from_name(c.name) == ref.id for c in cards):
                    raise ValueError(f"{ref.id} is not a business objective of {scope}")
                text = ref.id
            if text not in found:
                found.append(text)
    return found


def build(
    root: Path,
    scope: str,
    title: str,
    scopes: list[str] | None = None,
    template: str | None = None,
    taken: list[str] | None = None,
    bo: list[str] | None = None,
) -> tuple[str, Path, str]:
    """Allocate the next epic and render it; nothing is written. Returns (id, path, text)."""
    if not root.is_dir() or (root / "workspace.yaml").exists():
        raise ValueError("scope-root must be an existing, resolved project directory")
    if not ids.is_scope(scope) or not title.strip() or len(title) > 100 or "\n" in title:
        raise ValueError("provide an uppercase scope and a single-line title of 1..100 characters")
    participants = scopes or [scope]
    if scope not in participants or not all(ids.is_scope(s) for s in participants):
        raise ValueError("scopes must be valid and include the home scope")
    serves = objectives(root, scope, bo)
    identity = ids.next_id("EPIC", taken if taken is not None else ids.taken_ids(root))
    fm, body = frontmatter.split(template or DEFAULT_TEMPLATE)
    if fm is None:
        raise ValueError("template requires front matter")
    fm.update(
        {
            "id": identity,
            "type": "epic",
            "scope": scope,
            "title": title,
            "aliases": [],
            "status": "draft",
            "bo": serves,
            "scopes": participants,
        }
    )
    path = root / "01-analysis" / "epics" / ids.record_filename(identity, title)
    return identity, path, frontmatter.render(fm, body)


def create(
    root: Path,
    scope: str,
    title: str,
    scopes: list[str] | None = None,
    template: str | None = None,
    bo: list[str] | None = None,
) -> Path:
    identity, path, text = build(root, scope, title, scopes, template, bo=bo)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a reservation made by another writer during allocation.
    with path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(text)
    _ = identity
    return path


def set_objectives(root: Path, scope: str, epic: str, values: list[str]) -> Path:
    """Replace the business objectives of an existing epic, keeping everything else."""
    path = ids.find_record(root / "01-analysis" / "epics", epic)
    if path is None:
        raise ValueError(f"{epic} is not an epic of {scope}")
    serves = objectives(root, scope, values)
    path.write_text(
        frontmatter.update(path.read_text(encoding="utf-8"), {"bo": serves}),
        encoding="utf-8",
        newline="",
    )
    return path
