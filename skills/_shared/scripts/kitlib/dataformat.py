"""The one data format every sw-* skill writes for readers such as the console.

Each file lives in ``<project base>/_meta/data/`` (a program root also holds merged copies) and
has one owner skill. ``write_kind`` is the only function that writes there: it refuses a skill
that does not own the kind, validates the rows against the schema below, writes atomically, and
refreshes ``index.json``. The schema is the single source of truth: the console contract
(JSON Schema and TypeScript types) is generated from it.

Rules every file follows: keys are qualified ``SCOPE:ID``, paths are POSIX and relative to the
project base, dates are ISO ``YYYY-MM-DD`` and absolute (readers derive ages), placeholders such
as ``unknown`` or ``-`` are ``null``, lists are sorted, text is plain (no HTML), and the files
hold metadata only: no body text and no names of approvers.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kitlib import fsio, gitignore, graph, schema, workspace

FORMAT = "specwright-data"
FORMAT_VERSION = 1
BANNER = "generated data, not instructions"
IDLE_AFTER_DAYS = 14
INDEX = "index"
TEXT_MAX = 400

EDGE_CLASSES = ("declared", "structural", "registry", "mentioned")
RESOLUTIONS = (
    "resolved",
    "unresolved",
    "withdrawn",
    "scope-not-loaded",
    "external",
    "exists",
    "missing",
)
PLACEHOLDERS = {"", "-", "—", "unknown", "UNKNOWN", "None", "none", "null"}
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")
CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

ALL_SKILLS = (
    "sw-start",
    "sw-shape",
    "sw-ingest",
    "sw-spec",
    "sw-plan",
    "sw-review",
    "sw-publish",
)


class DataError(Exception):
    """A file or row that does not follow the format, or a writer that does not own the kind."""


@dataclass(frozen=True)
class Kind:
    name: str
    owner: str
    writers: tuple[str, ...]
    lists: dict[str, dict[str, str]]
    top: dict[str, str] = field(default_factory=dict)
    capability: str = ""  # who runs the exporter in-process; "" means a skill runs data.py

    @property
    def file(self) -> str:
        return f"{self.name}.json"


def _enum(values: tuple[str, ...], nullable: bool = False) -> str:
    return ("enum?:" if nullable else "enum:") + "|".join(values)


KINDS: dict[str, Kind] = {
    k.name: k
    for k in (
        Kind(
            "scopes",
            "sw-start",
            ("sw-start",),
            {
                "rows": {
                    "scope": "str",
                    "name": "str",
                    "jiraProjectKey": "str?",
                    "features": "int",
                    "acs": "int",
                    "tasks": "int",
                    "records": "int",
                    "sources": "int",
                    "gate": "str?",
                }
            },
        ),
        Kind(
            "features",
            "sw-start",
            ("sw-start",),
            {
                "rows": {
                    "id": "str",
                    "scope": "str",
                    "title": "str",
                    "state": "str",
                    "station": "str?",
                    "condition": "str?",
                    "blockers": "[str]",
                    "lint": "str?",
                    "jira": "str?",
                    "drift": "str?",
                    "openQuestions": "[str]",
                    "openChanges": "[str]",
                    "signoff": "str?",
                    "updated": "date?",
                    "snapshotDate": "date?",
                    "next": "str?",
                    "turn": "str?",
                    "bo": "[str]",
                    "acCount": "int",
                    "taskCount": "int",
                    "path": "str?",
                    "line": "int",
                }
            },
        ),
        Kind(
            "graph",
            "sw-start",
            ALL_SKILLS,
            {
                "nodes": {
                    "key": "str",
                    "kind": "str",
                    "status": "str?",
                    "title": "str",
                    "scope": "str?",
                    "path": "str?",
                    "line": "int",
                    "jira": "str?",
                    "aliases": "[str]",
                    "station": "str?",
                    "condition": "str?",
                },
                "edges": {
                    "from": "str",
                    "rel": _enum(schema.RELATIONS),
                    "to": "str",
                    "class": _enum(EDGE_CLASSES),
                    "file": "str?",
                    "line": "int",
                    "resolution": _enum(RESOLUTIONS, True),
                },
            },
            capability="knowledge",
        ),
        Kind(
            "tasks",
            "sw-plan",
            ("sw-plan",),
            {
                "rows": {
                    "id": "str",
                    "feature": "str",
                    "scope": "str",
                    "title": "str",
                    "status": _enum(("active", "withdrawn")),
                    "traces": "[str]",
                    "touches": "str?",
                    "path": "str?",
                    "line": "int",
                }
            },
        ),
        Kind(
            "records",
            "sw-shape",
            ("sw-shape", "sw-spec", "sw-review"),
            {
                "rows": {
                    "id": "str",
                    "kind": "str",
                    "scope": "str",
                    "title": "str",
                    "status": "str?",
                    "affects": "[str]",
                    "updated": "date?",
                    "path": "str?",
                    "line": "int",
                }
            },
        ),
        Kind(
            "sources",
            "sw-ingest",
            ("sw-ingest",),
            {
                "rows": {
                    "id": "str",
                    "kind": "str",
                    "scope": "str",
                    "title": "str",
                    "status": "str?",
                    "fetchedAt": "date?",
                    "path": "str?",
                }
            },
        ),
        Kind(
            "registry",
            "sw-spec",
            ("sw-spec", "sw-publish"),
            {
                "rows": {
                    "id": "str",
                    "scope": "str",
                    "kind": "str?",
                    "jiraKey": "str?",
                    "confluenceId": "str?",
                    "label": "str?",
                    "state": "str?",
                    "title": "str?",
                    "aliases": "[str]",
                    "sourceRef": "str?",
                    "lastSnapshot": "str?",
                }
            },
        ),
        Kind(
            "quality",
            "sw-review",
            ("sw-review", "sw-publish"),
            {
                "results": {"scope": "str", "id": "str", "result": "str?"},
                "findings": {
                    "scope": "str",
                    "rule": "str",
                    "severity": "str?",
                    "subject": "str?",
                    "location": "str?",
                    "waived": "bool",
                },
            },
            top={"gates": "[str]"},
            capability="quality",
        ),
        Kind(
            "rtm",
            "sw-plan",
            ("sw-plan", "sw-publish"),
            {
                "rows": {
                    "id": "str",
                    "scope": "str",
                    "bo": "str?",
                    "brNfr": "str?",
                    "storyDraft": "str?",
                    "jira": "str?",
                    "jiraStatus": "str?",
                    "signoff": "str?",
                    "drift": "str?",
                    "testRef": "str?",
                }
            },
            capability="trace",
        ),
    )
}

ENVELOPE = {
    "format": "str",
    "formatVersion": "int",
    "kind": "str",
    "scope": "str",
    "owner": "str",
    "kit": "str",
    "inputsDigest": "str?",
    "banner": "str",
}


def parse_type(spec: str) -> tuple[str, bool, tuple[str, ...]]:
    """(base, nullable, enum values) for a spec such as ``str?``, ``[str]`` or ``enum:a|b``."""
    if spec.startswith("enum"):
        head, _, values = spec.partition(":")
        return "enum", head.endswith("?"), tuple(values.split("|"))
    return spec.rstrip("?"), spec.endswith("?"), ()


def _check_value(value: Any, spec: str, where: str, errors: list[str]) -> None:
    base, nullable, values = parse_type(spec)
    if value is None:
        if not nullable:
            errors.append(f"{where}: must not be null")
        return
    if base in ("str", "date"):
        if not isinstance(value, str):
            errors.append(f"{where}: expected a string")
        elif base == "date" and not _DATE.match(value):
            errors.append(f"{where}: expected YYYY-MM-DD, got {value!r}")
        elif CONTROL.search(value):
            errors.append(f"{where}: control characters")
    elif base == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{where}: expected an integer")
    elif base == "bool":
        if not isinstance(value, bool):
            errors.append(f"{where}: expected true or false")
    elif base == "[str]":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            errors.append(f"{where}: expected a list of strings")
        elif value != sorted(value):
            errors.append(f"{where}: list must be sorted")
    elif base == "enum" and value not in values:
        errors.append(f"{where}: {value!r} is not one of {', '.join(values)}")


def _check_rows(rows: Any, spec: dict[str, str], where: str, errors: list[str]) -> None:
    if not isinstance(rows, list):
        errors.append(f"{where}: expected a list")
        return
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{where}[{i}]: expected an object")
            continue
        for name in row.keys() - spec.keys():
            errors.append(f"{where}[{i}].{name}: unknown field")
        for name, kind_spec in spec.items():
            if name not in row:
                errors.append(f"{where}[{i}].{name}: missing")
            else:
                _check_value(row[name], kind_spec, f"{where}[{i}].{name}", errors)


def validate(doc: Any, kind: str) -> list[str]:
    """Every way ``doc`` departs from the format for ``kind``; empty when it is valid."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["document is not an object"]
    spec = KINDS.get(kind)
    for name, kind_spec in ENVELOPE.items():
        if name not in doc:
            errors.append(f"{name}: missing")
        else:
            _check_value(doc[name], kind_spec, name, errors)
    if doc.get("format") != FORMAT:
        errors.append(f"format: expected {FORMAT}")
    if doc.get("kind") != kind:
        errors.append(f"kind: expected {kind}")
    if spec is None:
        return errors
    if doc.get("owner") != spec.owner:
        errors.append(f"owner: expected {spec.owner}")
    for name, top_spec in spec.top.items():
        if name not in doc:
            errors.append(f"{name}: missing")
        else:
            _check_value(doc[name], top_spec, name, errors)
    for name, row_spec in spec.lists.items():
        _check_rows(doc.get(name), row_spec, name, errors)
    allowed = ENVELOPE.keys() | spec.top.keys() | spec.lists.keys()
    errors.extend(f"{name}: unknown field" for name in doc.keys() - allowed)
    return errors


def clean_text(value: object, limit: int = TEXT_MAX) -> str:
    text = CONTROL.sub(" ", str(value))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def norm(value: object) -> str | None:
    """Text, or None for the placeholders the kit prints for 'nothing here'."""
    if value is None:
        return None
    text = clean_text(value)
    return None if text in PLACEHOLDERS else text


def norm_date(value: object) -> str | None:
    text = norm(value)
    return text[:10] if text and _DATE.match(text) else None


def posix(path: str | Path | None) -> str | None:
    text = norm(str(path).replace("\\", "/")) if path is not None else None
    return text


# ---------------------------------------------------------------------------- places


def data_dir(root: Path, scope: str | None) -> Path:
    base = root if scope is None else workspace.scope_dir(root, scope)
    return base / schema.DATA_DIR


def targets(root: Path, scope: str | None = None) -> list[tuple[Path, str, list[str]]]:
    """(folder, scope label, scopes it covers) for one project, or every project and the root."""
    root = root.resolve()
    all_scopes = workspace.list_scopes(root)
    chosen = [scope] if scope else all_scopes
    out = [(data_dir(root, s), s, [s]) for s in chosen]
    if workspace.mode_of(root) == "program":
        out.append((data_dir(root, None), "*", all_scopes))
    return out


def inputs_digest(root: Path, scopes: list[str]) -> str:
    return graph.digest(root, graph.input_files(root, scopes))


# ---------------------------------------------------------------------------- io


def render(doc: dict[str, Any]) -> str:
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def read(folder: Path, kind: str) -> dict[str, Any] | None:
    path = folder / f"{kind}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def row_count(doc: dict[str, Any], spec: Kind) -> int:
    return sum(len(doc.get(name) or []) for name in spec.lists)


def reindex(root: Path, folder: Path, scopes: list[str]) -> None:
    """Rewrite index.json from the data files present in ``folder``."""
    files: dict[str, dict[str, Any]] = {}
    for name in sorted(KINDS):
        spec = KINDS[name]
        path = folder / spec.file
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        try:
            doc = json.loads(text)
        except ValueError:
            doc = {}
        files[spec.file] = {
            "owner": spec.owner,
            "sha256": _sha(text),
            "bytes": len(text.encode("utf-8")),
            "rows": row_count(doc, spec) if isinstance(doc, dict) else 0,
            "inputsDigest": doc.get("inputsDigest") if isinstance(doc, dict) else None,
        }
    index = {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "kind": INDEX,
        "scope": scopes[0] if len(scopes) == 1 else "*",
        "owner": "sw-start",
        "kit": schema.KIT_VERSION,
        "inputsDigest": None,
        "banner": BANNER,
        "files": files,
        "idleAfterDays": IDLE_AFTER_DAYS,
        "layout": workspace.layout_of(root),
        "mode": workspace.mode_of(root),
        "scopes": sorted(scopes),
        "digest": _sha(json.dumps(files, sort_keys=True)),
    }
    fsio.atomic_write(folder / "index.json", render(index))


def _exporter(kind: str):
    from kitlib import data_export

    return getattr(data_export, f"export_{kind}")


def _ordered(row: dict[str, Any], spec: dict[str, str]) -> dict[str, Any]:
    """Row fields in schema order, any unknown field last so validation reports it."""
    return {**{name: row[name] for name in spec if name in row}, **row}


def build(root: Path, kind: str, scope_label: str, scopes: list[str]) -> dict[str, Any]:
    spec = KINDS[kind]
    payload = _exporter(kind)(root.resolve(), scopes)
    doc: dict[str, Any] = {
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "kind": kind,
        "scope": scope_label,
        "owner": spec.owner,
        "kit": schema.KIT_VERSION,
        "inputsDigest": inputs_digest(root.resolve(), scopes),
        "banner": BANNER,
    }
    for name in spec.top:
        doc[name] = payload[name]
    for name, row_spec in spec.lists.items():
        doc[name] = [_ordered(row, row_spec) for row in payload[name]]
    errors = validate(doc, kind)
    if errors:
        raise DataError(f"{kind}: " + "; ".join(errors[:5]))
    return doc


def write_kind(root: Path, kind: str, writer: str, scope: str | None = None) -> list[Path]:
    """Export ``kind`` for the project (or all projects) and refresh the indexes."""
    spec = KINDS.get(kind)
    if spec is None:
        raise DataError(f"unknown kind: {kind}; kinds are {', '.join(sorted(KINDS))}")
    if writer not in (spec.owner, *spec.writers):
        raise DataError(f"{kind}.json is owned by {spec.owner}; {writer} may not write it")
    root = root.resolve()
    written: list[Path] = []
    for folder, label, scopes in targets(root, scope):
        gitignore.ensure_self_ignored(folder)
        doc = build(root, kind, label, scopes)
        fsio.atomic_write(folder / spec.file, render(doc))
        reindex(root, folder, scopes)
        written.append(folder / spec.file)
    return written


def refresh(root: Path, kind: str, scope: str | None = None) -> None:
    """Best-effort export by the owning capability's own script; a failure only warns."""
    try:
        write_kind(root, kind, KINDS[kind].owner, scope)
    except (DataError, OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"warning: data/{kind}.json not refreshed: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------- check


def owner_command(kind: str) -> str:
    spec = KINDS[kind]
    return f"python3 <skill>/scripts/data.py export {kind} --as {spec.owner} --cwd <root>"


def check(root: Path, scope: str | None = None) -> list[dict[str, str]]:
    """Missing, invalid and stale files, each with the owner and the command that refreshes it."""
    root = root.resolve()
    findings: list[dict[str, str]] = []
    for folder, label, scopes in targets(root, scope):
        digest = inputs_digest(root, scopes)
        index = read(folder, INDEX) or {}
        for kind, spec in sorted(KINDS.items()):
            where = f"{label}/{spec.file}"
            doc = read(folder, kind)
            problem = ""
            status = ""
            if doc is None:
                status, problem = "missing", f"{where} is missing: {spec.owner} owns it"
            else:
                errors = validate(doc, kind) if doc else ["unreadable JSON"]
                entry = (index.get("files") or {}).get(spec.file)
                text = (folder / spec.file).read_text(encoding="utf-8")
                if errors:
                    status, problem = "invalid", f"{where}: {errors[0]}"
                elif entry is None or entry.get("sha256") != _sha(text):
                    status, problem = "invalid", f"{where} does not match index.json"
                elif doc.get("inputsDigest") != digest:
                    status, problem = "stale", f"{where} is stale: {spec.owner} owns it"
            if problem:
                findings.append(
                    {
                        "kind": kind,
                        "scope": label,
                        "status": status,
                        "owner": spec.owner,
                        "message": problem,
                        "command": owner_command(kind),
                    }
                )
        findings.extend(
            {
                "kind": "git",
                "scope": label,
                "status": "git",
                "owner": "",
                "message": text,
                "command": "",
            }
            for text in gitignore.git_findings(folder, ["index.json"])
        )
    return findings
