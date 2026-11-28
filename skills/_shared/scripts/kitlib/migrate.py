"""Move a project written in an earlier layout to one folder per item.

    _meta/                          -> .metadata/
    01-analysis/epics/EPIC-N--s.md  -> epics/EPIC-N/EPIC-N--s.md
    02-drafts/FEAT-N.*              -> features/FEAT-N/
    02-drafts/review/FEAT-N.*       -> features/FEAT-N/review/
    02-drafts/foundation/*          -> features/<foundation feature>/foundation/
    03-plan/FEAT-N.tasks.md         -> tasks/FEAT-N/
    03-plan/prompts/FEAT-N/*        -> tasks/FEAT-N/prompts/
    03-plan/FEAT-N.plan.md          -> plans/FEAT-N/

`plan` lists the moves and changes nothing; `apply` performs them. A destination that already
exists is never overwritten: the move is reported as a conflict and skipped. Running it twice
moves nothing the second time.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from kitlib import frontmatter, paths

_FEAT = re.compile(r"^(FEAT-\d{3})(?=[.\-])")
_FEAT_DIR = re.compile(r"^FEAT-\d{3}$")
_EPIC = re.compile(r"^(EPIC-\d{3})(?=--|\.)")
_OLD_LINK = "](../diagrams/"
_NEW_LINK = "](../../diagrams/"


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []


def _foundation_feature(base: Path) -> str | None:
    for story in sorted((base / paths.LEGACY_DRAFTS).glob("FEAT-*.story.md")):
        fm = frontmatter.parse(story.read_text(encoding="utf-8")).fm or {}
        if fm.get("kind") == "foundation":
            return story.name.split(".")[0]
    return None


def plan(base: Path) -> list[tuple[Path, Path]]:
    """Every (source, destination) file move this project needs, in a stable order."""
    moves: list[tuple[Path, Path]] = []
    old_meta = base / "_meta"
    if old_meta.is_dir():
        moves += [(p, base / ".metadata" / p.relative_to(old_meta)) for p in _files(old_meta)]
    for path in _files(base / paths.LEGACY_EPICS):
        match = _EPIC.match(path.name)
        if match:
            moves.append((path, paths.epic_dir(base, match.group(1)) / path.name))
    drafts = base / paths.LEGACY_DRAFTS
    foundation = _foundation_feature(base)
    for path in _files(drafts):
        rel = path.relative_to(drafts)
        top = rel.parts[0]
        head = _FEAT.match(rel.name)
        if top == paths.REVIEW and len(rel.parts) == 2 and head:
            moves.append((path, paths.review_dir(base, head.group(1)) / rel.name))
        elif top == paths.FOUNDATION and foundation:
            moves.append((path, paths.foundation_dir(base, foundation) / Path(*rel.parts[1:])))
        elif len(rel.parts) == 1 and head:
            moves.append((path, paths.feature_dir(base, head.group(1)) / rel.name))
    old_plan = base / paths.LEGACY_PLAN
    for path in _files(old_plan):
        rel = path.relative_to(old_plan)
        head = _FEAT.match(rel.name)
        if rel.parts[0] == paths.PROMPTS and len(rel.parts) >= 3 and _FEAT_DIR.match(rel.parts[1]):
            feat = rel.parts[1]
            moves.append((path, paths.prompts_dir(base, feat) / Path(*rel.parts[2:])))
        elif len(rel.parts) == 1 and head:
            target = paths.plan_dir if rel.name.endswith(".plan.md") else paths.tasks_dir
            moves.append((path, target(base, head.group(1)) / rel.name))
    return moves


def conflicts(moves: list[tuple[Path, Path]]) -> list[tuple[Path, Path]]:
    return [(s, d) for s, d in moves if d.exists()]


def apply(base: Path) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
    """Perform the planned moves; return (moved, skipped because the destination exists)."""
    moved: list[tuple[Path, Path]] = []
    skipped: list[tuple[Path, Path]] = []
    for src, dst in plan(base):
        if dst.exists():
            skipped.append((src, dst))
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append((src, dst))
        if dst.name.endswith((".story.md", ".card.md")):
            text = dst.read_text(encoding="utf-8")
            if _OLD_LINK in text:
                dst.write_text(text.replace(_OLD_LINK, _NEW_LINK), encoding="utf-8", newline="")
    for old in ("_meta", paths.LEGACY_EPICS, paths.LEGACY_DRAFTS, paths.LEGACY_PLAN):
        _prune(base / old)
    return moved, skipped


def _prune(folder: Path) -> None:
    """Remove a folder left holding only empty folders and .gitkeep files."""
    if not folder.is_dir():
        return
    for child in sorted(folder.rglob(".gitkeep")):
        child.unlink()
    for child in sorted(folder.rglob("*"), reverse=True):
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()
    if not any(folder.iterdir()):
        folder.rmdir()
