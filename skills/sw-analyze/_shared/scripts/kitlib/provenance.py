"""Amend where a snapshot says it came from, without touching its bytes or its file.

A snapshot with the right text but a wrong or missing source, version or URL would otherwise
carry bad provenance forever, because an identical re-import is a duplicate. An amendment is
appended to `_meta/provenance/<SRC-ID>.jsonl`; the snapshot file stays as written and readers
merge the amendments over its header with `effective`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kitlib import frontmatter, hashing, ids

FIELDS = ("source", "source_version", "remote_url", "remote_id", "tracker_key")
FOLDER = "_meta/provenance"


class ProvenanceError(ValueError):
    pass


def path_for(base: Path, src_id: str) -> Path:
    return base / FOLDER / f"{src_id}.jsonl"


def history(base: Path, src_id: str) -> list[dict[str, Any]]:
    path = path_for(base, src_id)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def effective(base: Path, src_id: str, fm: dict[str, Any]) -> dict[str, Any]:
    """The snapshot header with every amendment applied in order; `aliases` only ever grow."""
    merged = dict(fm)
    aliases = list(merged.get("aliases") or [])
    for entry in history(base, src_id):
        for name, value in entry["fields"].items():
            merged[name] = value
            if name in ("remote_id", "remote_url", "tracker_key") and value not in aliases:
                aliases.append(value)
    merged["aliases"] = aliases
    return merged


def _original_intact(base: Path, fm: dict[str, Any]) -> None:
    digest = str(fm.get("sha256", ""))
    raws = sorted((base / "00-inbox/raw").glob(digest[:12] + "-*")) if digest else []
    if not raws or not any(hashing.bytes_hash(p.read_bytes()) == digest for p in raws):
        raise ProvenanceError("the original bytes are missing or changed; amend nothing")


def plan(
    base: Path,
    src_id: str,
    fields: dict[str, str],
    by: str,
    reason: str,
    now: datetime | None = None,
) -> tuple[Path, str]:
    """Validate and return `(file, line to append)`; nothing is written."""
    if not ids.matches_type("snapshot", src_id):
        raise ProvenanceError(f"'{src_id}' is not a snapshot ID")
    path = ids.find_record(base / "00-inbox", src_id)
    if path is None:
        raise ProvenanceError(f"no snapshot {src_id}")
    fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
    fields = {
        k: " ".join(str(v).split()) for k, v in fields.items() if v is not None and str(v).strip()
    }
    unknown = set(fields) - set(FIELDS)
    if unknown or not fields:
        raise ProvenanceError(f"amend one or more of: {', '.join(FIELDS)}")
    if not " ".join(by.split()) or not " ".join(reason.split()):
        raise ProvenanceError("an amendment names who made it and why")
    _original_intact(base, fm)
    before = effective(base, src_id, fm)
    changed = {k: v for k, v in fields.items() if str(before.get(k, "")) != v}
    if not changed:
        raise ProvenanceError("nothing to amend: the provenance already says this")
    entry = {
        "amended_at": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "by": " ".join(by.split()),
        "reason": " ".join(reason.split()),
        "fields": changed,
        "previous": {k: before.get(k, "") for k in changed},
    }
    return path_for(base, src_id), json.dumps(entry, sort_keys=True) + "\n"


def append(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
