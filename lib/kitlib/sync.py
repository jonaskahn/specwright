"""Save immutable remote snapshots and classify drift without remote writes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from kitlib import adf, frontmatter, hashing, jira_diff, tables

INJECTION = re.compile(
    r"ignore (?:all )?previous instructions|run this command|"
    r"agent:\s*(?:set|update|publish|delete)",
    re.I,
)
MACROS = re.compile(r"<ac:structured-macro[^>]*ac:name=\"([\w-]+)\"", re.I)


class SyncError(ValueError):
    """A snapshot cannot be trusted as a complete representation of its source."""


def utc_name(key: str, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{key}@{stamp}.md"


def snapshot_text(issue: dict, body: str, warnings: list[str]) -> str:
    fields = issue.get("fields", {})
    fm = {
        "id": "SRC-0000",
        "type": "snapshot",
        "source_kind": "jira-issue",
        "source": issue.get("key", "UNKNOWN"),
        "source_version": str(fields.get("updated", "unknown")),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": hashing.bytes_hash(json.dumps(issue, sort_keys=True).encode()),
        "converter": "adf_to_md 0.1 (kit)",
        "status": "raw",
        "warnings": warnings,
    }
    return frontmatter.render(fm, body + "\n")


def pull(port, key: str) -> tuple[dict, str, list[str]]:
    issue = port.get_issue(key)
    description = issue.get("fields", {}).get("description")
    body, warnings = (
        adf.adf_to_md(description)
        if isinstance(description, dict)
        else (str(description or ""), [])
    )
    comments = port.list_comments(key)
    for comment in comments:
        text = str(comment.get("body", ""))
        if INJECTION.search(text):
            warnings.append("possible-injection")
    issue["comments"] = comments
    issue["changelog"] = port.list_changelog(key)
    return issue, body, warnings


def save_snapshot(base: Path, key: str, text: str, now: datetime | None = None) -> Path:
    """Refuse to overwrite any existing snapshot, including a same-second name."""
    folder = base / "snapshots/jira"
    folder.mkdir(parents=True, exist_ok=True)
    name = utc_name(key, now)
    path = folder / name
    number = 1
    while path.exists():
        path = folder / f"{key}@{name.split('@')[1][:-3]}-{number:02d}.md"
        number += 1
    path.write_text(text, encoding="utf-8")
    return path


def update_local(base: Path, scope_id: str, key: str, snapshot: Path, classes: list[str]) -> None:
    registry = base / "_meta/id-registry.md"
    doc = tables.parse(registry.read_text(encoding="utf-8"))
    doc.table.upsert(
        scope_id, {"Jira key": key, "Last snapshot": str(snapshot), "State": "published"}
    )
    registry.write_text(doc.render(), encoding="utf-8")
    matrix = base / "_meta/rtm.md"
    report = tables.parse(matrix.read_text(encoding="utf-8"))
    report.table.upsert(scope_id, {"Drift [sw-sync]": ", ".join(classes) or "none"})
    matrix.write_text(report.render(), encoding="utf-8")


def macro_warnings(storage: str, depth: int, pages: int) -> list[str]:
    manifest_limits = {"child_depth": 2, "max_pages": 50}
    if depth > manifest_limits["child_depth"] or pages > manifest_limits["max_pages"]:
        raise SyncError("Confluence child depth or page count exceeds its limit")
    names = MACROS.findall(storage)
    warnings = []
    for name in names:
        if name in {"info", "note", "warning", "tip", "panel", "expand", "code", "jira"}:
            continue
        warnings.append(f"unresolved-macro:{name}")
    return warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["classify"])
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        base = json.loads(args.base.read_text(encoding="utf-8"))
        current = json.loads(args.current.read_text(encoding="utf-8"))
        print(json.dumps(jira_diff.classify(base, current)))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
