#!/usr/bin/env python3
"""Link bare ids in epic feature tables and dependency lines.

A second run changes nothing. Ids inside an existing link or code span are left alone.
Exit codes: 0 done, 2 usage or workspace error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import links, paths, workspace  # noqa: E402


def fix_text(text: str, from_path: Path, base: Path) -> str:
    """Link ids in an epic Features table and in dependency lines."""
    section = ""
    fenced = False
    out = []
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith("```"):
            fenced = not fenced
            out.append(line)
            continue
        heading = re.match(r"^## (.+?)\s*$", line.rstrip("\n"))
        if heading and not fenced:
            section = heading.group(1).strip()
            out.append(line)
            continue
        linkify = not fenced and (
            stripped.startswith("Depends on:")
            or section == "Dependencies and relations"
            or (section == "Features" and stripped.startswith("|"))
        )
        out.append(links.linkify_line(line, from_path, base) if linkify else line)
    return "".join(out)


def fix_tree(base: Path) -> list[str]:
    changed = []
    targets = list(paths.stories(base))
    epic_root = paths.epics_dir(base)
    if epic_root.is_dir():
        targets += sorted(epic_root.glob("EPIC-*/*.md"))
    targets += paths.tasks_files(base)
    for path in targets:
        original = path.read_text(encoding="utf-8")
        updated = fix_text(original, path, base)
        if updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            changed.append(path.relative_to(base).as_posix())
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fix"])
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        root = workspace.find_root(args.root.resolve())
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, cwd=args.root.resolve(), write=True)
        for rel in fix_tree(workspace.scope_dir(root, scope)):
            print(rel)
        return 0
    except (OSError, ValueError, workspace.WorkspaceError, workspace.AskUser) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
