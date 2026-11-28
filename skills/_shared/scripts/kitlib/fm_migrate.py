"""Rewrite story and epic front matter onto the current contract.

`migrate.sh` replaces an installed kit. `kitlib.migrate` moves old folders. This module
rewrites documents. A story whose Identity hash does not match its body is refused.
"""

from __future__ import annotations

import re
from pathlib import Path

from kitlib import frontmatter, hashing, markdown, paths

_LEGACY = re.compile(r"^F\d{2}\.\d{2}$")
_PRIORITY = {
    "must": "must",
    "should": "should",
    "could": "could",
    "high": "must",
    "medium": "should",
    "low": "could",
}
_DROPPED = (
    "jira_summary",
    "jira_issuetype",
    "jira_parent",
    "jira_labels",
    "jira_priority",
    "original_priority",
    "source_fid",
)
_EPIC_SECTIONS = ("Done when", "Scope", "Risks", "Open questions")
_HASH = re.compile(r"Draft hash:\s*(sha256:[0-9a-f]{64})")


class MigrateError(ValueError):
    """This file cannot be mapped onto the current contract."""


def migrate_text(text: str) -> str:
    """Return the migrated document, or raise MigrateError."""
    fm, body = frontmatter.split(text)
    if not fm:
        raise MigrateError("no front matter")
    if fm.get("type") == "feature" and not fm.get("card"):
        return _story(text, fm, body)
    if fm.get("type") == "epic":
        return _epic(fm, body)
    return text


def migrate_tree(base: Path, dry_run: bool = False) -> tuple[list[str], list[str]]:
    """Migrate every story and epic under a project. Returns (written, refused)."""
    written, refused = [], []
    targets = list(paths.stories(base))
    epic_root = paths.epics_dir(base)
    if epic_root.is_dir():
        targets += sorted(epic_root.glob("EPIC-*/*.md"))
    for path in targets:
        rel = path.relative_to(base).as_posix()
        try:
            updated = migrate_text(path.read_text(encoding="utf-8"))
        except (MigrateError, frontmatter.FrontMatterError, OSError, UnicodeError) as exc:
            refused.append(f"{rel}: {exc}")
            continue
        if updated == path.read_text(encoding="utf-8"):
            continue
        written.append(rel)
        if not dry_run:
            path.write_text(updated, encoding="utf-8", newline="")
    return written, refused


def _story(text: str, fm: dict, body: str) -> str:
    recorded = _HASH.search(text)
    if recorded and recorded.group(1) != hashing.draft_hash(text):
        raise MigrateError("Identity draft hash does not match the body")
    if "priority" not in fm:
        for key in ("original_priority", "jira_priority"):
            mapped = _PRIORITY.get(str(fm.get(key) or "").strip().casefold())
            if mapped:
                fm["priority"] = mapped
                break
    legacy = [str(item) for item in fm.get("legacy_ids") or []]
    source_fid = str(fm.get("source_fid") or "")
    if _LEGACY.match(source_fid) and source_fid not in legacy:
        legacy.append(source_fid)
    for alias in fm.get("aliases") or []:
        if _LEGACY.match(str(alias)) and str(alias) not in legacy:
            legacy.append(str(alias))
    if legacy:
        fm["legacy_ids"] = legacy
    epic = fm.get("epic")
    if isinstance(epic, list):
        if len(epic) > 1:
            raise MigrateError("epic list has more than one id")
        fm["epic"] = epic[0] if epic else None
    if recorded:
        fm["draft_hash"] = recorded.group(1)
    for key in _DROPPED:
        fm.pop(key, None)
    body = markdown.drop_section(body, "DoR checklist")
    body = markdown.drop_section(body, "Identity")
    return hashing.stamp(frontmatter.render(fm, body))


def _epic(fm: dict, body: str) -> str:
    names = {section.name for section in markdown.iter_sections(body)}
    for name in _EPIC_SECTIONS:
        if name not in names:
            body = body.rstrip() + f"\n\n## {name}\n\nNone — not yet compiled.\n"
    return frontmatter.render(fm, body)
