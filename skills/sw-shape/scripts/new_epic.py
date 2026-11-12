#!/usr/bin/env python3
"""Reserve the next epic in one scope without replacing an existing file.

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
_shared = _source_shared if _source_shared.is_dir() else _local_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, ids  # noqa: E402


def create(root, scope, title, scopes=None, template=None):
    if not root.is_dir() or (root / "workspace.yaml").exists():
        raise ValueError("scope-root must be an existing, resolved project directory")
    if not ids.is_scope(scope) or not title.strip() or len(title) > 100 or "\n" in title:
        raise ValueError("provide an uppercase scope and a single-line title of 1..100 characters")
    participants = scopes or [scope]
    if scope not in participants or not all(ids.is_scope(s) for s in participants):
        raise ValueError("scopes must be valid and include the home scope")
    taken = []
    for path in sorted(root.rglob("*.md")):
        taken.extend(ref.id for ref in ids.find_refs(path.read_text(encoding="utf-8")))
        taken.extend(ref.id for ref in ids.find_refs(path.name))
    candidate = ids.next_id("EPIC", taken)
    template = template or _here.parent / "assets" / "epic.md"
    if not template.is_file():
        raise ValueError("template unavailable; provide --template pointing to assets/epic.md")
    fm, body = frontmatter.split(template.read_text(encoding="utf-8"))
    if fm is None:
        raise ValueError("template requires front matter")
    fm.update(
        {
            "id": candidate,
            "type": "epic",
            "scope": scope,
            "title": title,
            "status": "draft",
            "scopes": participants,
        }
    )
    target = root / "01-analysis" / "epics" / f"{candidate}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a reservation made by another writer during allocation.
    with target.open("x", encoding="utf-8", newline="") as handle:
        handle.write(frontmatter.render(fm, body))
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--scopes", help="comma-separated projects taking part, home first")
    parser.add_argument("--template", type=Path)
    args = parser.parse_args(argv)
    try:
        participants = [s.strip() for s in args.scopes.split(",")] if args.scopes else None
        print(create(args.scope_root, args.scope, args.title, participants, args.template))
        return 0
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
