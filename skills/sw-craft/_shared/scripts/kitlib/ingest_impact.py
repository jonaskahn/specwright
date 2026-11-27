"""Evidence association proposals and immutable backups, not automatic revisions."""

from __future__ import annotations

import json
import re
from pathlib import Path

from kitlib import frontmatter, graph_query, hashing, ids, workspace


def candidates(store: graph_query.Store, text: str) -> list[dict]:
    """Lexical overlap is a suggestion, even when there is only one result."""
    if store.freshness() != "fresh":
        raise ValueError("association suggestions require a fresh graph")
    words = set(re.findall(r"[\w-]{4,}", text.lower()))
    results = []
    for node in store.nodes():
        if node["kind"] not in ("feat", "epic") or node["status"] in ("withdrawn", "superseded"):
            continue
        overlap = words & set(re.findall(r"[\w-]{4,}", node["title"].lower()))
        if overlap:
            results.append({"target": node["key"], "reason": sorted(overlap), "confirmed": False})
    return sorted(results, key=lambda r: (-len(r["reason"]), r["target"]))


def propose(base: Path, source: str, target: str, source_quote: str, claim_quote: str) -> Path:
    """Save a CR proposal only; no requirement edits, revisions or approval."""
    scope = workspace.load(base / "project.yaml")["scope"]
    key = target if ":" in target else f"{scope}:{target}"
    ref = ids.parse_ref(key)
    if not ref or ref.scope != scope or not ids.matches_type("feature", ref.id):
        raise ValueError("impact target must be a feature in this scope")
    source_ref = ids.parse_ref(source)
    if (
        not source_ref
        or (source_ref.scope and source_ref.scope != scope)
        or not source_ref.id.startswith("SRC-")
    ):
        raise ValueError("impact requires a local source snapshot")
    snapshot = ids.find_record(base / "00-inbox", source_ref.id)
    if snapshot is None:
        raise ValueError(f"no snapshot file for {source_ref.id}")
    story = base / "02-drafts" / f"{ref.id}.story.md"
    if snapshot.is_symlink() or story.is_symlink():
        raise ValueError("impact input must not be a symlink")
    source_text = frontmatter.parse(snapshot.read_text(encoding="utf-8"))
    if source_text.error or not source_text.fm or source_text.fm.get("degraded"):
        raise ValueError("resolve degraded or invalid extraction before proposing an impact")
    story_text = story.read_text(encoding="utf-8")
    if (
        not source_quote.strip()
        or source_quote not in source_text.body
        or not source_text.body.strip()
    ):
        raise ValueError("source quotation is not present in extracted evidence")
    if not claim_quote.strip() or claim_quote not in frontmatter.parse(story_text).body:
        raise ValueError("claim quotation is not present in the saved story")
    # Quote hashes bind the proposed comparison; they do not establish its correctness.
    identity = hashing.text_hash(
        json.dumps([source_ref.id, key, source_quote, claim_quote, hashing.draft_hash(story_text)])
    )
    records = base / "records"
    records.mkdir(parents=True, exist_ok=True)
    for path in records.glob("CR-*.md"):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        if fm.get("proposal_hash") == identity:
            return path
    number = ids.next_id("CR", ids.taken_ids(base))
    title = f"Evidence impact on {key}"
    fm = {
        "id": number,
        "type": "cr",
        "title": title,
        "aliases": [],
        "scope": scope,
        "status": "proposed",
        "affects": [key],
        "sourced_from": [f"{scope}:{source_ref.id}"],
        "proposal_hash": identity,
        "spec_hash": hashing.draft_hash(story_text),
    }

    def quote(text):
        return "\n".join("> " + line for line in text.splitlines())

    body = (
        f"# Proposed evidence impact on {key}\n\n"
        f"## New evidence\n\n{quote(source_quote)}\n\n"
        f"## Saved claim\n\n{quote(claim_quote)}\n\n"
        "## Decision needed\n\nPotential conflict, not an accepted requirement change. "
        "Confirm relevance and the intended change through the owning skill.\n"
    )
    path = records / ids.record_filename(number, title)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(frontmatter.render(fm, body))
    return path


def occurrence(base: Path, source_id: str, digest: str, origin: str, version: str) -> Path:
    """Keep additional provenance without modifying an immutable SRC snapshot."""
    record = {"source_id": source_id, "sha256": digest, "origin": origin, "source_version": version}
    identity = hashing.bytes_hash(json.dumps(record, sort_keys=True).encode("utf-8"))
    path = base / "_meta/provenance" / f"{identity}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        from datetime import datetime, timezone

        record["observed_at"] = datetime.now(timezone.utc).isoformat()
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return path


def backup(base: Path, relative: str) -> Path:
    """Archive the exact current bytes immediately before an authorized edit."""
    path = workspace.safe_join(base, relative)
    if path.is_symlink() or not path.is_file():
        raise ValueError("backup requires an existing local artifact")
    if path.parts[len(base.resolve().parts)] not in ("01-analysis", "02-drafts", "03-plan"):
        raise ValueError("only authored artifacts may be revision-backed up")
    data = path.read_bytes()
    digest = hashing.bytes_hash(data)
    fm = frontmatter.parse(data.decode("utf-8")).fm or {}
    revision = str(fm.get("revision", "unversioned"))
    revision = re.sub(r"[^A-Za-z0-9_.-]", "_", revision)
    target = workspace.safe_join(base, f"_meta/history/{relative}/{revision}-{digest}.bak")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(data)
    except FileExistsError:
        if target.read_bytes() != data:
            raise ValueError("backup identity collision") from None
    return target
