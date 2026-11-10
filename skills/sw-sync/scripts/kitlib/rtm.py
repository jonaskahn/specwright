"""Trace indexes retain historical rows so withdrawn identities cannot be recycled."""

from __future__ import annotations

from dataclasses import dataclass, field
from kitlib import frontmatter, fsio, ids, markdown, schema, tables, workspace
from pathlib import Path
from typing import Any


class OwnershipError(ValueError):
    """A caller cannot replace another writer's evidence."""


@dataclass
class Entity:
    key: str
    kind: str
    path: Path
    fm: dict[str, Any]
    body: str
    refs: set[str] = field(default_factory=set)
    withdrawn: bool = False
    parent: str | None = None


def qualify(value: str, scope: str) -> str:
    ref = ids.parse_ref(value)
    if ref is None and ids.matches_type("idea", value):
        return ids.qualify(scope, value)
    if ref is None:
        raise ValueError(f"invalid spec reference: {value}")
    return ref.qualified if ref.scope else ids.qualify(scope, ref.id)


def documents(base: Path):
    """Imported snapshot text cannot establish local definitions."""
    for folder in ("00-inbox", "01-analysis", "02-drafts", "records", "snapshots"):
        for path in sorted((base / folder).rglob("*.md")):
            if "raw" not in path.relative_to(base).parts and not path.is_symlink():
                parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
                if parsed.error:
                    raise ValueError(f"{path}: {parsed.error}")
                if parsed.fm and parsed.fm.get("id"):
                    yield path, parsed.fm, parsed.body


def scan(root: Path) -> tuple[dict[str, Entity], list[str]]:
    entities: dict[str, Entity] = {}
    findings: list[str] = []
    for scope in workspace.list_scopes(root):
        for path, fm, body in documents(workspace.scope_dir(root, scope)):
            key = qualify(str(fm["id"]), scope)
            if fm.get("scope", scope) != scope:
                findings.append(f"{key} scope mismatch: {path}")
            kind = str(fm.get("type", "unknown"))
            refs = {qualify(str(r), scope) for r in ids.find_refs(str(fm) + chr(10) + body)}
            if kind in ("src", "snapshot"):
                refs.clear()
            refs.discard(key)
            entity = Entity(key, kind, path, fm, body, refs, fm.get("status") == "withdrawn")
            previous = entities.get(key)
            if previous:
                # A summary and its story share identity; two stories do not.
                if kind == previous.kind == "feature" and bool(fm.get("card")) != bool(
                        previous.fm.get("card")
                ):
                    if fm.get("card"):
                        continue
                else:
                    findings.append(f"{key} duplicate definition: {previous.path}, {path}")
                    continue
            entities[key] = entity
    for entity in list(entities.values()):
        if entity.kind != "feature" or entity.fm.get("card"):
            continue
        scope = entity.key.split(":")[0]
        section = markdown.sections(entity.body).get("Acceptance criteria")
        active = markdown.ac_blocks(section)
        removed = markdown.ac_tombstones(section)
        for ac in [*active, *removed]:
            key = qualify(ac, scope)
            if key in entities:
                findings.append(f"{key} duplicate criterion")
                continue
            parent = qualify(f"FEAT-{ac.split('-')[1]}", scope)
            if parent != entity.key:
                findings.append(f"{key} orphan: AC without matching FEAT")
            entity.refs.discard(key)
            entities[key] = Entity(
                key, "ac", entity.path, {}, "", {entity.key}, ac in removed, entity.key
            )
    for scope in workspace.list_scopes(root):
        plan = workspace.scope_dir(root, scope) / "03-plan"
        for path in sorted(plan.glob("*.tasks.md")) if plan.is_dir() else []:
            if not path.is_symlink():
                _scan_tasks(path, scope, entities, findings)
    return entities, findings


def _line_with(body: str, first_line: int, needle: str) -> int:
    for number, text in enumerate(body.splitlines(), first_line):
        if needle in text:
            return number
    return 0


def _scan_tasks(path: Path, scope: str, entities: dict[str, Entity], findings: list[str]) -> None:
    """Tasks live in one file per feature; the file names its feature in front matter."""
    parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
    if parsed.error:
        raise ValueError(f"{path}: {parsed.error}")
    feat = str((parsed.fm or {}).get("feat", ""))
    if not ids.matches_type("feature", feat.split(":")[-1]):
        findings.append(f"{path}: tasks file needs a feat: FEAT-NNN front matter field")
        return
    parent = qualify(feat, scope)
    blocks = markdown.task_blocks(parsed.body, parsed.body_line)
    removed = markdown.task_tombstones(parsed.body)
    for task in [*blocks, *removed]:
        key = qualify(task, scope)
        if key in entities:
            findings.append(f"{key} duplicate task")
            continue
        number = ids.parse_task(task)
        if number is None or ids.feat_number(parent.split(":")[1]) != number[0]:
            findings.append(f"{key} orphan: task without matching FEAT")
        block = blocks.get(task)
        refs = {parent}
        line = block.line if block else _line_with(parsed.body, parsed.body_line, task)
        details: dict[str, Any] = {"line": line, "title": ""}
        if block:
            details["title"] = block.title
            details["traces"] = block.field_line("Traces to")
            details["touches"] = block.field_line("Touches")
            refs |= {qualify(str(r), scope) for r in ids.find_refs(details["traces"])}
        refs.discard(key)
        entities[key] = Entity(key, "task", path, details, "", refs, task in removed, parent)


def read_table(path: Path, header: list[str]) -> tables.Document:
    if path.exists():
        doc = tables.parse(path.read_text(encoding="utf-8"))
        if doc.table is None or doc.table.header != header:
            raise ValueError(f"{path}: unexpected table columns")
        keys = [row[0] for row in doc.table.rows]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{path}: duplicate table rows")
        return doc
    return tables.Document(f"# {path.stem}\n\n", tables.Table(header), "")


def rtm_header() -> list[str]:
    return [schema.RTM_ID_COLUMN, *[f"{name} [{owner}]" for name, owner in schema.RTM_COLUMNS]]


def rebuild(root: Path, scope: str) -> list[str]:
    entities, findings = scan(root)
    if any("duplicate" in finding for finding in findings):
        raise ValueError("; ".join(findings))
    base = workspace.scope_dir(root, scope)
    matrix = read_table(base / "_meta/rtm.md", rtm_header())
    registry = read_table(base / "_meta/id-registry.md", list(schema.REGISTRY_COLUMNS))
    for key, entity in sorted(entities.items()):
        if key.split(":")[0] != scope:
            continue
        matrix.table.upsert(key)
        # Only identity shape belongs to row maintenance; remote evidence stays intact.
        if registry.table.find(key) is None:
            registry.table.upsert(
                key, {"Kind": "story" if entity.kind == "feature" else entity.kind}
            )
    fsio.atomic_write(base / "_meta/rtm.md", matrix.render())
    fsio.atomic_write(base / "_meta/id-registry.md", registry.render())
    return findings


def set_cell(root: Path, scope: str, key: str, column: str, value: str, skill: str) -> None:
    owners = dict(schema.RTM_COLUMNS)
    if column not in owners:
        raise ValueError(f"unknown RTM column: {column}")
    if owners[column] != skill:
        raise OwnershipError(f"{column} belongs to {owners[column]}, not {skill}")
    key = qualify(key, scope)
    if key.split(":")[0] != scope:
        raise ValueError("row scope differs from write scope")
    path = workspace.scope_dir(root, scope) / "_meta/rtm.md"
    doc = read_table(path, rtm_header())
    if doc.table.find(key) is None:
        raise ValueError(f"unknown row: {key}; rebuild first")
    doc.table.upsert(key, {f"{column} [{skill}]": value})
    fsio.atomic_write(path, doc.render())


REGISTRY_OWNERS = {
    "sw-trace": {"Kind"},
    "sw-spec": {"Kind", "State"},
    "sw-publish": {
        "Jira key",
        "Confluence id",
        "Label",
        "Entity property",
        "Last published draft hash",
        "Last snapshot",
        "State",
    },
    "sw-sync": {"Jira key", "Last snapshot", "State"},
}


def registry_upsert(path: Path, key: str, cells: dict[str, str], skill: str) -> None:
    unknown = set(cells) - set(schema.REGISTRY_COLUMNS[1:])
    if unknown:
        raise ValueError(f"unknown registry columns: {sorted(unknown)}")
    denied = set(cells) - REGISTRY_OWNERS.get(skill, set())
    if denied:
        raise OwnershipError(f"{skill} does not own registry columns: {sorted(denied)}")
    if not ids.parse_ref(key) or ":" not in key:
        raise ValueError("registry rows require qualified spec IDs")
    doc = read_table(path, list(schema.REGISTRY_COLUMNS))
    doc.table.upsert(key, cells)
    fsio.atomic_write(path, doc.render())


def jira_keys(root: Path) -> dict[str, str]:
    result = {}
    for scope in workspace.list_scopes(root):
        path = workspace.scope_dir(root, scope) / "_meta/id-registry.md"
        doc = read_table(path, list(schema.REGISTRY_COLUMNS))
        for row in doc.table.rows:
            value = row[doc.table.col("Jira key")]
            if value not in ("", tables.EMPTY, "unknown"):
                result[row[0]] = value
    return result


def check(root: Path, scope: str | None = None) -> list[str]:
    entities, findings = scan(root)
    keys = jira_keys(root)
    seen: dict[str, str] = {}
    for key, jira in keys.items():
        if ":FEAT-" in key:
            if jira in seen:
                findings.append(f"{key} duplicate Jira key {jira} with {seen[jira]} (L-037)")
            seen[jira] = key
    used = {ref for entity in entities.values() for ref in entity.refs}
    for key, entity in sorted(entities.items()):
        if scope and key.split(":")[0] != scope:
            continue
        if entity.withdrawn:
            findings.append(f"{key} tombstone: retained; never reuse")
            continue
        if entity.kind == "feature" and not entity.fm.get("bo"):
            findings.append(f"{key} orphan: no BO (L-005)")
        if entity.kind == "br" and key not in used:
            findings.append(f"{key} orphan: BR not used")
        for ref in sorted(entity.refs):
            if ref not in entities:
                findings.append(f"{key} dangling reference: {ref}")
            elif entities[ref].withdrawn:
                findings.append(f"{key} references tombstone: {ref}")
    for scope_name in workspace.list_scopes(root):
        if scope and scope != scope_name:
            continue
        base = workspace.scope_dir(root, scope_name)
        for filename, header in (
                ("rtm.md", rtm_header()),
                ("id-registry.md", list(schema.REGISTRY_COLUMNS)),
        ):
            doc = read_table(base / "_meta" / filename, header)
            for row in doc.table.rows:
                if row[0] not in entities:
                    findings.append(
                        f"{row[0]} historical row without definition: "
                        f"{filename}; retain as tombstone"
                    )
    return sorted(set(findings))


def impact(root: Path, target: str, scope: str) -> dict[str, list[str]]:
    entities, _ = scan(root)
    keys = jira_keys(root)
    if ids.parse_ref(target):
        seeds = {qualify(target, scope)}
        if not seeds <= entities.keys():
            raise ValueError(f"unknown ID: {target}")
    else:
        seeds = {key for key, jira in keys.items() if jira == target}
        if not seeds:
            raise ValueError(f"unknown Jira key: {target}")
    reached = set(seeds)
    while True:
        added = {key for key, entity in entities.items() if entity.refs & reached} - reached
        if not added:
            break
        reached |= added
    return {
        "features": sorted(key for key in reached if ":FEAT-" in key),
        "criteria": sorted(key for key in reached if ":AC-" in key),
        "jira": sorted({keys[key] for key in reached if key in keys}),
    }
