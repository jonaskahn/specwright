"""One exporter per data kind: map what the owner skill already reads into the schema.

Every exporter is ``export_<kind>(root, scopes) -> payload`` and only reads. It returns the lists
(and top-level fields) that ``dataformat.KINDS`` names for the kind; ``dataformat.write_kind``
orders, validates and writes them.
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from kitlib import (
    dataformat,
    frontmatter,
    graph,
    graph_query,
    ids,
    rtm,
    schema,
    tables,
    workspace,
)
from kitlib.dataformat import DataError, norm, norm_date, posix

RECORD_KINDS = ("q", "dec", "cr", "amendment")
SOURCE_KINDS = ("src", "snapshot")
_GATE = re.compile(r"Gate:\s*([a-z-]+)")
_SPLIT = re.compile(r"[|,;]")


def _base(root: Path, scope: str) -> Path:
    return workspace.scope_dir(root, scope)


def _rel(path: Path, base: Path) -> str | None:
    try:
        return posix(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return None


def _scope_of(key: str) -> str | None:
    head, sep, _ = key.partition(":")
    return head if sep and ids.is_scope(head) else None


def _in(key: str, scopes: list[str]) -> bool:
    return _scope_of(key) in scopes


def _list(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, (list, tuple, set)) else [value]
    return sorted({text for item in items if (text := norm(item))})


def _gate(base: Path) -> str | None:
    path = base / "_meta" / "lint-report.md"
    if not path.is_file():
        return None
    found = _GATE.search(path.read_text(encoding="utf-8"))
    return found.group(1) if found else None


def _entities(root: Path) -> dict[str, rtm.Entity]:
    try:
        return rtm.scan(root)[0]
    except ValueError as exc:
        raise DataError(f"cannot read the spec files: {exc}") from exc


def _table(base: Path, name: str, header: list[str]) -> list[list[str]]:
    try:
        doc = rtm.read_table(base / "_meta" / name, header)
    except ValueError as exc:
        raise DataError(str(exc)) from exc
    return doc.table.rows if doc.table else []


# ---------------------------------------------------------------------------- graph


def export_graph(root: Path, scopes: list[str]) -> dict[str, Any]:
    store = graph_query.Store(root, scopes[0] if len(scopes) == 1 else None)
    fresh = store.freshness()
    if fresh != "fresh":
        raise DataError(
            f"the knowledge graph is {fresh}; "
            f"run: python3 <skill>/_shared/scripts/graph.py build --cwd {root}"
        )
    nodes = []
    for node in store.nodes():
        loc, _, line = node["loc"].rpartition(":")
        if not line.isdigit():
            loc, line = node["loc"], "0"
        row: dict[str, Any] = {
            "key": node["key"],
            "kind": node["kind"],
            "status": norm(node["status"]),
            "title": dataformat.clean_text(node["title"]) or node["key"],
            "scope": _scope_of(node["key"]),
            "path": posix(loc),
            "line": int(line),
            "jira": None,
            "aliases": sorted({a for a in node.get("aliases", "").split("|") if a}),
            "station": None,
            "condition": None,
        }
        if node["kind"] == "feat":
            shard = store.shard(node)
            lifecycle = shard.get("lifecycle") or {}
            row["jira"] = norm(shard.get("jira"))
            row["station"] = norm(lifecycle.get("station"))
            row["condition"] = norm(lifecycle.get("condition"))
        nodes.append(row)
    edges = [
        {
            "from": e.src,
            "rel": e.rel,
            "to": e.dst,
            "class": e.cls,
            "file": posix(e.file),
            "line": e.line,
            "resolution": norm(e.res),
        }
        for e in store.edges("out")
    ]
    nodes.sort(key=lambda r: r["key"])
    edges.sort(
        key=lambda r: (
            r["from"],
            r["rel"],
            r["to"],
            r["class"],
            r["file"] or "",
            r["line"],
            r["resolution"] or "",
        )
    )
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------- features


def _status_module():
    scripts = Path(__file__).resolve().parent.parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import status  # noqa: PLC0415
    except ImportError as exc:  # a skill that does not ship the status capability
        raise DataError("features.json needs the status capability (sw-start ships it)") from exc
    return status


def _snapshot_date(base: Path, cell: str | None) -> str | None:
    if not cell or cell in dataformat.PLACEHOLDERS:
        return None
    candidate = (base / cell).resolve()
    if not candidate.is_relative_to(base.resolve()) or not candidate.is_file():
        return None
    fm = frontmatter.parse(candidate.read_text(encoding="utf-8")).fm or {}
    return norm_date(fm.get("fetched_at", fm.get("updated")))


def export_features(root: Path, scopes: list[str]) -> dict[str, Any]:
    status = _status_module()
    report = status.build_report(root, scopes, today=date(2000, 1, 1))
    entities = _entities(root)
    children: dict[str, int] = {}
    for entity in entities.values():
        if entity.kind in ("ac", "task") and not entity.withdrawn and entity.parent:
            key = f"{entity.parent}|{entity.kind}"
            children[key] = children.get(key, 0) + 1
    rows = []
    for item in report["features"]:
        key = item["id"]
        scope = key.split(":")[0]
        base = _base(root, scope)
        entity = entities.get(key)
        fm = entity.fm if entity else {}
        registry = _table(base, "id-registry.md", list(schema.REGISTRY_COLUMNS))
        cell = next(
            (
                row[schema.REGISTRY_COLUMNS.index("Last snapshot")]
                for row in registry
                if row[0] in (key, key.split(":", 1)[1])
            ),
            None,
        )
        rows.append(
            {
                "id": key,
                "scope": scope,
                "title": dataformat.clean_text(fm.get("title") or key),
                "state": str(item["state"]),
                "station": norm(item["station"]),
                "condition": norm(item["condition"]),
                "blockers": _list(item["blockers"]),
                "lint": norm(item["lint"]),
                "illustration": norm(item.get("illustration")),
                "jira": norm(item["jira"]),
                "drift": norm(item["drift"]),
                "openQuestions": _list(item["open_questions"]),
                "openChanges": _list(item["open_changes"]),
                "signoff": norm(item["signoff"]),
                "updated": norm_date(fm.get("updated")),
                "snapshotDate": _snapshot_date(base, cell),
                "next": norm(item["next"]),
                "turn": norm(item["turn"]),
                "bo": _list(fm.get("bo")),
                "acCount": children.get(f"{key}|ac", 0),
                "taskCount": children.get(f"{key}|task", 0),
                "path": _rel(entity.path, base) if entity else None,
                "line": 1,
            }
        )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


# ---------------------------------------------------------------------------- scopes


def export_scopes(root: Path, scopes: list[str]) -> dict[str, Any]:
    entities = _entities(root)
    rows = []
    for scope in scopes:
        base = _base(root, scope)
        manifest_file = base / workspace.FLAT_MANIFEST
        manifest = workspace.load(manifest_file) if manifest_file.is_file() else {}
        mine = [e for e in entities.values() if e.key.startswith(scope + ":") and not e.withdrawn]

        def count(*kinds: str, _mine=mine) -> int:
            return sum(1 for e in _mine if e.kind in kinds and not e.fm.get("card"))

        jira = manifest.get("jira") or {}
        rows.append(
            {
                "scope": scope,
                "name": dataformat.clean_text(manifest.get("name") or scope),
                "jiraProjectKey": norm(jira.get("project_key") if isinstance(jira, dict) else None),
                "features": count("feature"),
                "acs": count("ac"),
                "tasks": count("task"),
                "records": count(*RECORD_KINDS),
                "sources": count(*SOURCE_KINDS),
                "gate": _gate(base),
            }
        )
    rows.sort(key=lambda r: r["scope"])
    return {"rows": rows}


# ---------------------------------------------------------------------------- spec records


def export_tasks(root: Path, scopes: list[str]) -> dict[str, Any]:
    rows = []
    for entity in _entities(root).values():
        if entity.kind != "task" or not _in(entity.key, scopes):
            continue
        scope = entity.key.split(":")[0]
        base = _base(root, scope)
        rows.append(
            {
                "id": entity.key,
                "feature": entity.parent or "",
                "scope": scope,
                "title": dataformat.clean_text(entity.fm.get("title") or entity.key),
                "status": "withdrawn" if entity.withdrawn else "active",
                "traces": sorted(entity.refs - {entity.parent or ""}),
                "layer": norm(entity.fm.get("layer")),
                "touches": norm(entity.fm.get("touches")),
                "visuals": norm(entity.fm.get("visuals")),
                "path": _rel(entity.path, base),
                "line": int(entity.fm.get("line") or 0),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


def export_records(root: Path, scopes: list[str]) -> dict[str, Any]:
    rows = []
    for entity in _entities(root).values():
        if entity.kind not in RECORD_KINDS or not _in(entity.key, scopes):
            continue
        scope = entity.key.split(":")[0]
        rows.append(
            {
                "id": entity.key,
                "kind": entity.kind,
                "scope": scope,
                "title": dataformat.clean_text(entity.fm.get("title") or entity.key),
                "status": norm(entity.fm.get("status")),
                "affects": sorted(graph.declared_affects(entity.fm, scope)),
                "updated": norm_date(entity.fm.get("updated")),
                "path": _rel(entity.path, _base(root, scope)),
                "line": 1,
            }
        )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


def export_sources(root: Path, scopes: list[str]) -> dict[str, Any]:
    rows = []
    for entity in _entities(root).values():
        if entity.kind not in SOURCE_KINDS or not _in(entity.key, scopes):
            continue
        scope = entity.key.split(":")[0]
        rows.append(
            {
                "id": entity.key,
                "kind": entity.kind,
                "scope": scope,
                "title": dataformat.clean_text(entity.fm.get("title") or entity.key),
                "status": norm(entity.fm.get("status")),
                "fetchedAt": norm_date(entity.fm.get("fetched_at", entity.fm.get("updated"))),
                "path": _rel(entity.path, _base(root, scope)),
            }
        )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


# ---------------------------------------------------------------------------- tables


def export_registry(root: Path, scopes: list[str]) -> dict[str, Any]:
    columns = list(schema.REGISTRY_COLUMNS)

    def cell(row: list[str], name: str) -> str | None:
        return norm(row[columns.index(name)])

    rows = []
    for scope in scopes:
        for row in _table(_base(root, scope), "id-registry.md", columns):
            try:
                key = rtm.qualify(row[0], scope)
            except ValueError:
                key = f"{scope}:{row[0]}"
            rows.append(
                {
                    "id": key,
                    "scope": scope,
                    "kind": cell(row, "Kind"),
                    "jiraKey": cell(row, "Jira key"),
                    "confluenceId": cell(row, "Confluence id"),
                    "label": cell(row, "Label"),
                    "state": cell(row, "State"),
                    "title": cell(row, "Title"),
                    "aliases": _list(_SPLIT.split(row[columns.index("Aliases")])),
                    "sourceRef": cell(row, "Source ref"),
                    "lastSnapshot": cell(row, "Last snapshot"),
                }
            )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


def export_rtm(root: Path, scopes: list[str]) -> dict[str, Any]:
    names = ("bo", "brNfr", "storyDraft", "jira", "jiraStatus", "signoff", "drift", "testRef")
    rows = []
    for scope in scopes:
        for row in _table(_base(root, scope), "rtm.md", rtm.rtm_header()):
            try:
                key = rtm.qualify(row[0], scope)
            except ValueError:
                key = f"{scope}:{row[0]}"
            rows.append(
                {"id": key, "scope": scope}
                | {name: norm(row[i + 1]) for i, name in enumerate(names)}
            )
    rows.sort(key=lambda r: r["id"])
    return {"rows": rows}


def export_quality(root: Path, scopes: list[str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    gates: list[str] = []
    for scope in scopes:
        base = _base(root, scope)
        path = base / "_meta" / "lint-report.md"
        gate = _gate(base)
        if gate:
            gates.append(f"{scope}:{gate}")
        if not path.is_file():
            continue
        doc = tables.parse(path.read_text(encoding="utf-8"))
        table = doc.table
        if table is None:
            continue
        header = table.header

        def col(name: str, _header=header) -> int:
            return _header.index(name) if name in _header else -1

        for row in table.rows:
            if "Severity" in header:
                waiver = col("Waiver")
                findings.append(
                    {
                        "scope": scope,
                        "rule": dataformat.clean_text(row[0]),
                        "severity": norm(row[col("Severity")]),
                        "subject": norm(row[col("Subject")]) if col("Subject") >= 0 else None,
                        "location": norm(row[col("Location")]) if col("Location") >= 0 else None,
                        "waived": bool(waiver >= 0 and norm(row[waiver])),
                    }
                )
            elif len(row) > 1:
                try:
                    key = rtm.qualify(row[0], scope)
                except ValueError:
                    key = f"{scope}:{row[0]}"
                results.append({"scope": scope, "id": key, "result": norm(row[1])})
    results.sort(key=lambda r: (r["scope"], r["id"]))
    findings.sort(key=lambda r: (r["scope"], r["rule"], r["subject"] or "", r["location"] or ""))
    return {"results": results, "findings": findings, "gates": sorted(gates)}
