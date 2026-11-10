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
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import frontmatter, hashing, ids, markdown, schema  # noqa: E402


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
) -> Path:
    if not root.is_dir() or (root / "workspace.yaml").exists():
        raise ValueError("scope-root must be an existing, resolved project directory")
    if not ids.is_scope(scope) or not summary.strip() or len(summary) > 100 or "\n" in summary:
        raise ValueError(
            "provide an uppercase scope and a single-line summary of 1..100 characters"
        )
    taken = []
    for path in sorted(root.rglob("*.md")):
        taken.extend(ref.id for ref in ids.find_refs(path.read_text(encoding="utf-8")))
        taken.extend(ref.id for ref in ids.find_refs(path.name))
    candidate = ids.next_id("FEAT", taken)
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
        raise ValueError("template requires front matter and twelve canonical sections")
    original = original.replace("FEAT-NNN", candidate).replace("AC-NNN-", f"AC-{candidate[5:]}-")
    original = original.replace("<SCOPE>", scope)
    fm, body = frontmatter.split(original)
    fm.update(
        {
            "id": candidate,
            "type": "feature",
            "scope": scope,
            "status": "draft",
            "jira_summary": summary,
            "jira_issuetype": "Story",
            "jira_parent": parent,
            "jira_priority": "Medium",
            "jira_labels": ["specwright", f"feat:{candidate}", f"proj:{scope}"],
        }
    )
    output = frontmatter.render(fm, body)
    output = output.replace("<sha256:…>", hashing.draft_hash(output))
    target = root / "02-drafts" / f"{candidate}.story.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a reservation made by another writer during allocation.
    with target.open("x", encoding="utf-8", newline="") as handle:
        handle.write(output)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--feature", help="assert the next FEAT id; never selects a used id")
    parser.add_argument("--parent", default="None")
    args = parser.parse_args(argv)
    try:
        print(
            create(
                args.scope_root, args.scope, args.summary, args.template, args.feature, args.parent
            )
        )
        return 0
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
