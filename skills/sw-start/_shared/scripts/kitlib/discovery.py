"""Read-only, consent-gated repository context discovery; matches are proposals only."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from kitlib import frontmatter, inventory, workspace

DOC_EXT = {".md", ".mdx", ".rst", ".txt", ".adoc"}
DOC_DIRS = {
    "docs",
    "doc",
    "documentation",
    "wiki",
    "plans",
    "planning",
    "specs",
    "requirements",
    "adr",
    "adrs",
    "architecture",
}
SKIP = inventory.SKIP | {"raw", "secrets", "credentials", "private"}
SENSITIVE = re.compile(r"(?:secret|credential|password|token|private[-_]?key)", re.I)
IDENTITY = re.compile(r"\b(?:EPIC-\d{3}|FEAT-\d{3}|TASK-\d{3}-\d+|IMPL-\d{3})\b")
MAX_DEPTH = 6
MAX_ENTRIES = 20000
MAX_BYTES = inventory.MAX_BYTES


def offer() -> dict:
    """A prompt contract, not permission to inspect a repository."""
    return {
        "question": "How should we collect context for this change?",
        "options": [
            "discover repository docs and plans (recommended)",
            "use selected files or Specwright items",
            "describe the change first",
        ],
        "unanswered": "do not scan; leave context unresolved",
        "consent_required": True,
        "command": "analyze.py discover --cwd <repository> --confirm-scan",
    }


def _files(root: Path, *, spec: bool = False):
    """Prune before descending; never follow links or read excluded file contents."""

    def unreadable(error):
        raise ValueError(
            f"discovery cannot read {error.filename}; select readable directories"
        ) from error

    seen = 0
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=unreadable):
        here = Path(folder)
        rel = here.relative_to(root)
        seen += len(dirs) + len(files)
        if seen > MAX_ENTRIES:
            raise ValueError("discovery entry budget exceeded; select a smaller directory")
        dirs[:] = sorted(
            d
            for d in dirs
            if d not in SKIP
            and not d.startswith(".")
            and not SENSITIVE.search(d)
            and not (here / d).is_symlink()
            and len(rel.parts) < MAX_DEPTH
        )
        for name in sorted(files):
            path = here / name
            if path.is_symlink() or name.startswith(".") or SENSITIVE.search(name):
                continue
            if path.suffix.lower() not in DOC_EXT:
                continue
            if not spec and rel.parts and not any(p.lower() in DOC_DIRS for p in rel.parts):
                continue
            try:
                if path.stat().st_size > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield path


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _existing(spec_root: Path | None, scope: str | None) -> list[dict]:
    if spec_root is None:
        return []
    scopes = [scope] if scope else workspace.list_scopes(spec_root)
    if any(s not in workspace.list_scopes(spec_root) for s in scopes):
        raise ValueError("unknown scope; select a scope from the workspace")
    out = []
    for selected in scopes:
        base = workspace.scope_dir(spec_root, selected)
        for path in _files(base, spec=True):
            # Sources and analysis are evidence, not items to merge by inferred identity.
            rel = path.relative_to(base)
            if rel.parts[0] not in {"epics", "features", "tasks", "plans", "records"}:
                continue
            if any(
                p in {"review", "foundation", "prompts"} for p in rel.parts
            ) or path.name.endswith(".card.md"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            fm = frontmatter.parse(text).fm or {}
            identity = str(fm.get("id") or fm.get("feat") or "")
            if not identity:
                continue
            out.append(
                {
                    "scope": selected,
                    "id": identity,
                    "title": str(fm.get("title") or ""),
                    "path": path.relative_to(spec_root).as_posix(),
                    "sha256": _digest(path),
                }
            )
    return out


def discover(
    cwd: Path,
    *,
    consent: bool = False,
    scope: str | None = None,
    batch_size: int = 50,
    offset: int = 0,
    snapshot: str | None = None,
) -> dict:
    """Inventory docs without importing, approving, changing status or assigning links."""
    if batch_size < 1 or offset < 0:
        raise ValueError("batch_size must be positive and offset must be non-negative")
    if not consent:
        return {"state": "consent_required", **offer()}
    cwd = cwd.resolve()
    spec_root = workspace.find_root(cwd)
    repo = (
        workspace.code_repo_root(spec_root)
        if spec_root and cwd.is_relative_to(spec_root.resolve())
        else cwd
    )
    if repo is None or not repo.is_dir():
        raise ValueError("select an existing repository or documentation directory")
    items = _existing(spec_root, scope)
    docs = []
    for path in _files(repo):
        docs.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "sha256": _digest(path),
                "bytes": path.stat().st_size,
            }
        )
    fingerprint = hashlib.sha256(repr((str(repo), scope, docs, items)).encode()).hexdigest()
    if offset and not snapshot:
        raise ValueError("resuming discovery needs --snapshot from the first batch")
    if snapshot and snapshot != fingerprint:
        raise ValueError(
            "discovery sources changed; restart at offset 0 and reconfirm affected decisions"
        )
    proposed = []
    for doc in docs[offset : offset + batch_size]:
        # Do not emit raw target text: the agent reads selected files only after review.
        text = (repo / doc["path"]).read_text(encoding="utf-8", errors="replace")
        references = sorted(set(IDENTITY.findall(text)))
        words = set(inventory._words(Path(doc["path"]).stem))
        matches = []
        for item in items:
            exact = item["id"] in references
            overlap = words & set(inventory._words(item["title"]))
            if exact or overlap:
                matches.append(
                    {
                        **item,
                        "reason": "mentioned ID; not an accepted link"
                        if exact
                        else "filename/title overlap; identity unconfirmed",
                    }
                )
        proposed.append(
            {
                **doc,
                "mentioned_ids": references,
                "proposed_matches": matches,
                "authority": "unconfirmed",
                "decision": "pending",
            }
        )
    end = offset + len(proposed)
    return {
        "state": "review_required",
        "repository": str(repo),
        "snapshot": fingerprint,
        "batch_size": batch_size,
        "offset": offset,
        "total": len(docs),
        "next_offset": end if end < len(docs) else None,
        "documents": proposed,
        "existing_items": items,
        "choices": [
            "link as evidence",
            "extend unpublished feature",
            "propose change request",
            "create new feature",
            "exclude",
            "leave unresolved",
        ],
        "coverage": {
            "max_depth": MAX_DEPTH,
            "max_entries": MAX_ENTRIES,
            "max_file_bytes": MAX_BYTES,
            "formats": sorted(DOC_EXT),
            "excluded": (
                "hidden, generated, dependency, sensitive-name and symlink paths; "
                "unrelated directories; original bytes are not retained"
            ),
            "limitations": (
                "names and explicit references only; no semantic identity, authority, "
                "implementation or completion is inferred; "
                "unsupported formats need selected-file import"
            ),
        },
        "writes": [],
    }
