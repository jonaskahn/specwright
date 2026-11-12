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


def build(
    root: Path,
    scope: str,
    title: str,
    scopes: list[str] | None = None,
    template: str | None = None,
    taken: list[str] | None = None,
) -> tuple[str, Path, str]:
    """Allocate the next epic and render it; nothing is written. Returns (id, path, text)."""
    if not root.is_dir() or (root / "workspace.yaml").exists():
        raise ValueError("scope-root must be an existing, resolved project directory")
    if not ids.is_scope(scope) or not title.strip() or len(title) > 100 or "\n" in title:
        raise ValueError("provide an uppercase scope and a single-line title of 1..100 characters")
    participants = scopes or [scope]
    if scope not in participants or not all(ids.is_scope(s) for s in participants):
        raise ValueError("scopes must be valid and include the home scope")
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
) -> Path:
    identity, path, text = build(root, scope, title, scopes, template)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a reservation made by another writer during allocation.
    with path.open("x", encoding="utf-8", newline="") as handle:
        handle.write(text)
    _ = identity
    return path
