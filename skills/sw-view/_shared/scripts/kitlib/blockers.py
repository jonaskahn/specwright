"""Open questions that block a feature, read straight from the records (no graph needed)."""

from __future__ import annotations

from pathlib import Path

from kitlib import frontmatter, graph, schema


def blocking_questions(base: Path, scope: str, feat_id: str) -> list[tuple[str, str]]:
    """`(question ID, title)` for every open, blocking question that names the feature."""
    found = []
    for path in sorted((base / "records").glob("Q-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        if fm.get("type") != "q" or fm.get("status") not in schema.OPEN_Q:
            continue
        if not graph.is_blocking(fm):
            continue
        if f"{scope}:{feat_id}" in graph.declared_affects(fm, scope):
            found.append((str(fm.get("id", path.stem)), str(fm.get("title", ""))))
    return found
