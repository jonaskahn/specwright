"""Epic allocation shared by the shaping script and the record tools."""

from __future__ import annotations

import re
from pathlib import Path

from kitlib import frontmatter, ids, links, markdown, paths

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

## Done when

<measurable exit criteria, or a Q>

## Scope

**In scope**

- <what this epic includes>

**Out of scope**

- <what it excludes> — reason: <why>

## Features

| ID | Title | Priority | Status | Depends on |
| --- | --- | --- | --- | --- |

## Risks

None — not yet compiled.

## Open questions

None — not yet compiled.

## Projects involved

<Home project and any other project whose features join this epic, with the reason.>

## Jira

<Existing Jira key if the ID registry maps one, else None. Only a shipped epic is published.>
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
                cards = (root / "analysis").rglob("*.md")
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
    path = paths.epic_dir(root, identity) / ids.record_filename(identity, title)
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


def feature_rows(body: str) -> list[dict[str, object]]:
    """Rows of a generated Features table. An empty or placeholder section has none."""
    section = markdown.sections(body).get("Features")
    if section is None:
        return []
    rows = []
    for line in section.text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or cells[0].lower() == "id" or set(cells[0]) <= set("-: "):
            continue
        feat = re.search(r"FEAT-\d{3}", cells[0])
        if not feat:
            continue
        rows.append(
            {
                "id": feat.group(0),
                "title": cells[1],
                "priority": cells[2],
                "status": cells[3],
                "depends_on": sorted(set(re.findall(r"FEAT-\d{3}", cells[4]))),
            }
        )
    return rows


def refresh_features(base: Path) -> list[Path]:
    """Rewrite each epic's Features table from the stories that name it."""
    folder = paths.epics_dir(base)
    if not folder.is_dir():
        return []
    stories = []
    for path in paths.stories(base):
        parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
        if parsed.fm and parsed.fm.get("type") == "feature" and not parsed.fm.get("card"):
            stories.append((path, parsed.fm))
    changed = []
    for path in sorted(folder.glob("EPIC-*/*.md")):
        if _refresh_one(base, path, stories):
            changed.append(path)
    return changed


def _refresh_one(base: Path, path: Path, stories: list[tuple[Path, dict]]) -> bool:
    text = path.read_text(encoding="utf-8")
    fm, body = frontmatter.split(text)
    if not fm or fm.get("type") != "epic":
        return False
    epic = str(fm.get("id") or "")
    members = [(story, story_fm) for story, story_fm in stories if _names_epic(story_fm, epic)]
    rows = [
        "| ID | Title | Priority | Status | Depends on |",
        "| --- | --- | --- | --- | --- |",
    ]
    sources: list[str] = []
    for _story, story_fm in members:
        feat = str(story_fm.get("id") or "")
        linked = links.link_for(feat, path, base) or feat
        deps = []
        for dep in story_fm.get("depends_on") or []:
            ident = str(dep).split(":")[-1]
            deps.append(links.link_for(ident, path, base) or ident)
        rows.append(
            "| {id} | {title} | {priority} | {status} | {deps} |".format(
                id=linked,
                title=str(story_fm.get("title") or ""),
                priority=str(story_fm.get("priority") or ""),
                status=str(story_fm.get("status") or ""),
                deps=", ".join(deps) if deps else "None",
            )
        )
        for source in story_fm.get("sources") or []:
            ident = str(source).split(":")[-1]
            if ident not in sources:
                sources.append(ident)
    if members:
        fm["sources"] = sources
    table = "\n".join(rows)
    updated = frontmatter.render(fm, _replace_section(body, "Features", table))
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8", newline="")
    return True


def _names_epic(fm: dict, epic: str) -> bool:
    raw = fm.get("epic")
    values = raw if isinstance(raw, list) else [raw]
    return any(str(item).split(":")[-1] == epic for item in values if item)


def _replace_section(body: str, name: str, content: str) -> str:
    pattern = re.compile(rf"(^## {re.escape(name)}\n)(.*?)(?=^## |\Z)", re.M | re.S)
    block = "\n" + content.strip() + "\n\n"
    if pattern.search(body):
        return pattern.sub(lambda match: match.group(1) + block, body, count=1)
    return body.rstrip() + f"\n\n## {name}\n{block}"


def set_objectives(root: Path, scope: str, epic: str, values: list[str]) -> Path:
    """Replace the business objectives of an existing epic, keeping everything else."""
    path = ids.find_record(paths.epic_dir(root, epic), epic)
    if path is None:
        raise ValueError(f"{epic} is not an epic of {scope}")
    serves = objectives(root, scope, values)
    path.write_text(
        frontmatter.update(path.read_text(encoding="utf-8"), {"bo": serves}),
        encoding="utf-8",
        newline="",
    )
    return path
