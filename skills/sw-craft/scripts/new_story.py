#!/usr/bin/env python3
"""Reserve the next feature in one scope without replacing an existing file.

Exit codes: 0 created, 1 invalid content or allocation conflict, 2 usage or file error.
The scope-root argument is an already resolved project directory, not a program root.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import (  # noqa: E402
    blockers,
    frontmatter,
    hashing,
    ids,
    markdown,
    paths,
    rtm,
    schema,
)


def default_template() -> Path | None:
    bundled = _here.parent / "assets" / "jira-story.md"
    return bundled if bundled.is_file() else None


def create(
    root: Path,
    scope: str,
    summary: str,
    template: Path | None = None,
    feature: str | None = None,
    parent: str = "None",
    epic: list[str] | None = None,
    idea: list[str] | None = None,
    reserved: str | None = None,
    source: str | None = None,
    legacy: str | None = None,
    bo: str | None = None,
) -> Path:
    if not root.is_dir() or (root / "workspace.yaml").exists():
        raise ValueError("scope-root must be an existing, resolved project directory")
    _ = parent  # publish derives the Jira parent from the epic; it is not stored
    aliases: list[str] = []
    if reserved:
        # A feature reserved earlier (for example from a legacy register) keeps its ID, its
        # title and its aliases; no new number is allocated.
        if not ids.matches_type("feature", reserved):
            raise ValueError("--reserved takes a feature ID such as FEAT-002")
        row = rtm.read_table(root / ".metadata/id-registry.md", list(schema.REGISTRY_COLUMNS)).table
        key = f"{scope}:{reserved}"
        if row.find(key) is None or row.value(key, "State") in ("withdrawn", "superseded"):
            raise ValueError(f"{reserved} is not a reserved feature of {scope}")
        if (paths.story(root, reserved)).exists():
            raise ValueError(f"{reserved} already has a story")
        summary = summary or row.value(key, "Title")
        aliases = [a for a in row.value(key, "Aliases").split("|") if a]
        if source:
            if not legacy or not bo:
                raise ValueError("--from needs --legacy and --bo")
            from kitlib import compile as compiler
            from kitlib import workspace

            project = workspace.find_root(root) or root
            epic_id = epic[0] if epic else None
            return compiler.write_reserved(
                project,
                scope,
                source,
                [item.strip() for item in legacy.split(",") if item.strip()],
                reserved,
                bo,
                epic_id,
            )
    if not ids.is_scope(scope) or not summary.strip() or len(summary) > 100 or "\n" in summary:
        raise ValueError(
            "provide an uppercase scope and a single-line summary of 1..100 characters"
        )
    candidate = reserved or ids.next_id("FEAT", ids.taken_ids(root))
    ids.feat_number(candidate)
    if feature and feature != candidate:
        raise ValueError(f"next allocatable feature is {candidate}; existing IDs cannot be reused")
    template = template or default_template()
    if template is None:
        raise ValueError(
            "template unavailable; provide --template pointing to assets/jira-story.md"
        )
    original = template.read_text(encoding="utf-8")
    fm, body = frontmatter.split(original)
    if fm is None or [s.name for s in markdown.iter_sections(body)] != schema.STORY_SECTIONS:
        raise ValueError("template requires front matter and the canonical story sections")
    original = original.replace("FEAT-NNN", candidate).replace("AC-NNN-", f"AC-{candidate[5:]}-")
    original = original.replace("<SCOPE>", scope)
    fm, body = frontmatter.split(original)
    fm.update(
        {
            "id": candidate,
            "type": "feature",
            "scope": scope,
            "title": summary,
            "aliases": aliases,
            "status": "draft",
            "priority": "should",
            "jira_key": None,
        }
    )
    if epic:
        fm["epic"] = epic[0] if len(epic) == 1 else list(epic)
    if idea:
        fm["idea"] = list(idea)
    output = hashing.stamp(frontmatter.render(fm, body))
    target = paths.story(root, candidate)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a reservation made by another writer during allocation.
    with target.open("x", encoding="utf-8", newline="") as handle:
        handle.write(output)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--summary", help="required unless --reserved supplies the title")
    parser.add_argument("--reserved", help="specify an already reserved feature, e.g. FEAT-002")
    parser.add_argument("--template", type=Path)
    parser.add_argument("--feature", help="assert the next FEAT id; never selects a used id")
    parser.add_argument("--parent", default="None")
    parser.add_argument(
        "--epic", action="append", help="epic this feature belongs to, e.g. REF:EPIC-001"
    )
    parser.add_argument("--idea", action="append", help="idea this feature was shaped from")
    parser.add_argument(
        "--from", dest="source", help="SRC id to compile instead of the blank template"
    )
    parser.add_argument("--legacy", help="comma-separated source feature ids, e.g. F04.06,F04.07")
    parser.add_argument("--bo", help="BO-NNN required when compiling from a snapshot")
    args = parser.parse_args(argv)
    try:
        if not args.summary and not args.reserved:
            raise ValueError("give --summary, or --reserved to take the title from the registry")
        target = create(
            args.scope_root,
            args.scope,
            args.summary or "",
            args.template,
            args.feature,
            args.parent,
            args.epic,
            args.idea,
            args.reserved,
            args.source,
            args.legacy,
            args.bo,
        )
        print(target)
        waiting = blockers.blocking_questions(
            args.scope_root, args.scope, target.name.split(".")[0]
        )
        for question, title in waiting:
            print(f"warning: blocking question {question} is open: {title}", file=sys.stderr)
        return 0
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
