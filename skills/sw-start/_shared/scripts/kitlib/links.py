"""Relative Markdown links for spec ids that already have a file.

A missing id is left alone. Callers that need a line citation use kitlib.cite, not this module.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from kitlib import ids, paths, rtm, schema, tables

_SKIP = {".git", ".metadata", "raw", "node_modules", "__pycache__"}


def _file_named(base: Path, spec_id: str) -> Path | None:
    """`<id>.md` or `<id>--<slug>.md` anywhere under base, except generated and raw trees."""
    for folder in ("sources", "analysis", "epics", "features", "records", "assets"):
        found = ids.find_record(base / folder, spec_id)
        if found is not None:
            return found
        nested = base / folder
        if nested.is_dir():
            named = sorted(p for p in nested.rglob(f"{spec_id}--*.md") if p.is_file())
            if named:
                return named[0]
            exact = sorted(p for p in nested.rglob(f"{spec_id}.md") if p.is_file())
            if exact:
                return exact[0]
    return None


def _asset_file(base: Path, spec_id: str) -> Path | None:
    registry = base / ".metadata/asset-registry.md"
    if not registry.is_file():
        return None
    try:
        doc = rtm.read_table(registry, list(schema.ASSET_REGISTRY_COLUMNS))
    except (OSError, ValueError):
        return None
    file_col = doc.table.col("File")
    for row in doc.table.rows:
        if row[0].split(":")[-1] != spec_id:
            continue
        rel = row[file_col].strip()
        if not rel or rel == tables.EMPTY:
            return None
        path = base / rel
        return path if path.is_file() else None
    return None


def resolve(spec_id: str, base: Path) -> tuple[Path, str] | None:
    """The file and optional fragment a spec id points at, or None when it has no file."""
    spec_id = spec_id.split(":")[-1]
    ac = ids.parse_ac(spec_id)
    if ac:
        feat = f"FEAT-{ac[0]:03d}"
        path = paths.story(base, feat)
        return (path, spec_id.lower()) if path.is_file() else None
    task = ids.parse_task(spec_id)
    if task:
        feat = f"FEAT-{task[0]:03d}"
        path = paths.tasks_file(base, feat)
        return (path, spec_id.lower()) if path.is_file() else None
    if ids.matches_type("feature", spec_id):
        path = paths.story(base, spec_id)
        return (path, "") if path.is_file() else None
    if ids.matches_type("epic", spec_id):
        path = ids.find_record(paths.epic_dir(base, spec_id), spec_id)
        return (path, "") if path is not None else None
    if spec_id.startswith("ASSET-"):
        path = _asset_file(base, spec_id)
        return (path, "") if path is not None else None
    if spec_id.startswith(("Q-", "DEC-", "CR-", "AMD-", "RISK-")):
        path = ids.find_record(base / "records", spec_id)
        return (path, "") if path is not None else None
    path = _file_named(base, spec_id)
    if path is None or _SKIP & set(path.relative_to(base).parts):
        return None
    return path, ""


def link_for(spec_id: str, from_path: Path, base: Path) -> str | None:
    """A relative link `[ID](path)`, or None when the id does not resolve to a file."""
    found = resolve(spec_id.split(":")[-1], base)
    if found is None:
        return None
    target, fragment = found
    rel = Path(os.path.relpath(target, Path(from_path).parent)).as_posix()
    href = f"{rel}#{fragment}" if fragment else rel
    label = spec_id.split(":")[-1]
    return f"[{label}]({href})"


def linkify_line(line: str, from_path: Path, base: Path) -> str:
    """Link bare ids on one line. Ids already inside a link or code span stay put.

    A citation `SRC-0001:L12#abcd` is not a link target: the id is followed by `:L`.
    """
    protected = [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`|\[[^\]]*\]\([^)]*\)", line)]

    def covered(index: int) -> bool:
        return any(start <= index < end for start, end in protected)

    for match in reversed(list(ids._REF.finditer(line))):
        if covered(match.start()) or line[match.end() : match.end() + 2] == ":L":
            continue
        rendered = link_for(match.group(2), from_path, base)
        if rendered:
            line = line[: match.start()] + rendered + line[match.end() :]
    return line
