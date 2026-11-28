"""Where every work item lives inside one project folder.

One folder per item, grouped by kind, so an agent opens the folder of the item it works on and
nothing else:

    epics/EPIC-001/EPIC-001--slug.md
    features/FEAT-001/FEAT-001.story.md   .card.md   .feature   review/   foundation/
    tasks/FEAT-001/FEAT-001.tasks.md      prompts/
    plans/FEAT-001/FEAT-001.plan.md

Every other module asks this one; no other module spells these folder names.
"""

from __future__ import annotations

from pathlib import Path

EPICS = "epics"
FEATURES = "features"
TASKS = "tasks"
PLANS = "plans"
ITEM_FOLDERS = (EPICS, FEATURES, TASKS, PLANS)
PROMPTS = "prompts"
REVIEW = "review"
FOUNDATION = "foundation"
INDEX = "INDEX.md"
ITEM_META = ".metadata/item.json"

# The folders earlier versions used for the same items; read only by the migration.
LEGACY_DRAFTS = "02-drafts"
LEGACY_PLAN = "03-plan"
LEGACY_EPICS = "01-analysis/epics"


def epics_dir(base: Path) -> Path:
    return base / EPICS


def epic_dir(base: Path, epic: str) -> Path:
    return base / EPICS / epic


def features_dir(base: Path) -> Path:
    return base / FEATURES


def feature_dir(base: Path, feat: str) -> Path:
    return base / FEATURES / feat


def story(base: Path, feat: str) -> Path:
    return feature_dir(base, feat) / f"{feat}.story.md"


def card(base: Path, feat: str) -> Path:
    return feature_dir(base, feat) / f"{feat}.card.md"


def feature_file(base: Path, feat: str) -> Path:
    return feature_dir(base, feat) / f"{feat}.feature"


def review_dir(base: Path, feat: str) -> Path:
    return feature_dir(base, feat) / REVIEW


def foundation_dir(base: Path, feat: str) -> Path:
    return feature_dir(base, feat) / FOUNDATION


def tasks_dir(base: Path, feat: str) -> Path:
    return base / TASKS / feat


def tasks_file(base: Path, feat: str) -> Path:
    return tasks_dir(base, feat) / f"{feat}.tasks.md"


def prompts_dir(base: Path, feat: str) -> Path:
    return tasks_dir(base, feat) / PROMPTS


def plan_dir(base: Path, feat: str) -> Path:
    return base / PLANS / feat


def plan_file(base: Path, feat: str) -> Path:
    return plan_dir(base, feat) / f"{feat}.plan.md"


def stories(base: Path) -> list[Path]:
    """Every story file, in feature order."""
    return sorted(base.glob(f"{FEATURES}/FEAT-*/FEAT-*.story.md"))


def story_ids(base: Path) -> list[str]:
    return [p.name.split(".")[0] for p in stories(base)]


def cards(base: Path) -> list[Path]:
    return sorted(base.glob(f"{FEATURES}/FEAT-*/FEAT-*.card.md"))


def feature_files(base: Path) -> list[Path]:
    return sorted(base.glob(f"{FEATURES}/FEAT-*/FEAT-*.feature"))


def tasks_files(base: Path) -> list[Path]:
    return sorted(base.glob(f"{TASKS}/FEAT-*/FEAT-*.tasks.md"))


def tasks_ids(base: Path) -> set[str]:
    return {p.name.split(".")[0] for p in tasks_files(base)}


def plan_files(base: Path) -> list[Path]:
    return sorted(base.glob(f"{PLANS}/FEAT-*/FEAT-*.plan.md"))


def epic_files(base: Path) -> list[Path]:
    return sorted(base.glob(f"{EPICS}/EPIC-*/*.md"))


def item_dirs(base: Path) -> list[Path]:
    """Every folder that holds one work item (an epic, a feature, a task set or a plan)."""
    out: list[Path] = []
    for kind in ITEM_FOLDERS:
        root = base / kind
        if root.is_dir():
            out += sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    return out
