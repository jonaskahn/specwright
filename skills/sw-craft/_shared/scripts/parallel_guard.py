#!/usr/bin/env python3
"""Check that parallel workers wrote only the files they own.

snapshot  hash every file under a scope root into a JSON file (run before the workers)
verify    compare the tree with that snapshot and check every created, changed or deleted
          file against the workers' allow-lists (run after the workers, before any shared write)

An allow-list is NAME=PATTERN[,PATTERN...] with `/`-separated patterns relative to the scope
root. `*` and `?` match within one path segment only, so `02-drafts/FEAT-001.*` cannot reach
into a subfolder. A changed file that no worker owns is a stray write; one that two workers
own is a collision. Both fail the check.

Exit codes: 0 clean, 1 violations, 2 usage or file error.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import sys
from pathlib import Path

SKIP_PARTS = {".git", "__pycache__", "node_modules", ".DS_Store"}


def _tree(root: Path) -> dict[str, str]:
    """Relative POSIX path -> SHA-256 for every regular file under root."""
    if not root.is_dir():
        raise ValueError(f"{root} is not a directory")
    digests: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if SKIP_PARTS & set(rel.parts) or path.is_symlink() or not path.is_file():
            continue
        digests[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _matches(rel: str, pattern: str) -> bool:
    parts, wanted = rel.split("/"), pattern.strip("/").split("/")
    return len(parts) == len(wanted) and all(
        fnmatch.fnmatchcase(a, b) for a, b in zip(parts, wanted, strict=True)
    )


def parse_allow(items: list[str]) -> dict[str, list[str]]:
    allow: dict[str, list[str]] = {}
    for item in items:
        name, sep, patterns = item.partition("=")
        listed = [p for p in patterns.split(",") if p.strip()]
        if not sep or not name.strip() or not listed:
            raise ValueError(f"--allow expects NAME=PATTERN[,PATTERN...], got {item!r}")
        if name in allow:
            raise ValueError(f"worker {name} is listed twice")
        for pattern in listed:
            if pattern.startswith("/") or ".." in pattern.split("/"):
                raise ValueError(f"pattern {pattern!r} must be relative to the scope root")
        allow[name] = listed
    if not allow:
        raise ValueError("give at least one --allow")
    return allow


def compare(before: dict[str, str], after: dict[str, str], allow: dict[str, list[str]]) -> dict:
    """Classify each changed file: owned by one worker, stray, or contested."""
    changes = {p: "created" for p in after.keys() - before.keys()}
    changes.update({p: "deleted" for p in before.keys() - after.keys()})
    changes.update({p: "changed" for p in before.keys() & after.keys() if before[p] != after[p]})
    owned: dict[str, list[str]] = {name: [] for name in allow}
    stray: list[str] = []
    collisions: list[dict] = []
    for path in sorted(changes):
        owners = [n for n, pats in allow.items() if any(_matches(path, p) for p in pats)]
        if not owners:
            stray.append(path)
        elif len(owners) > 1:
            collisions.append({"path": path, "workers": sorted(owners)})
        else:
            owned[owners[0]].append(path)
    return {
        "changes": {p: changes[p] for p in sorted(changes)},
        "owned": owned,
        "stray": stray,
        "collisions": collisions,
        "ok": not stray and not collisions,
    }


def _report(result: dict) -> str:
    lines = []
    for name, paths in result["owned"].items():
        lines.append(f"{name}: {len(paths)} file(s)")
        lines.extend(f"  {result['changes'][p]} {p}" for p in paths)
    lines.extend(f"STRAY {result['changes'][p]} {p}: no worker owns it" for p in result["stray"])
    lines.extend(
        f"COLLISION {c['path']}: owned by {', '.join(c['workers'])}" for c in result["collisions"]
    )
    lines.append("clean" if result["ok"] else "violations found; reject the workers involved")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snap = sub.add_parser("snapshot", help="record the tree before the workers start")
    snap.add_argument("--scope-root", required=True, type=Path)
    snap.add_argument("--out", required=True, type=Path)
    ver = sub.add_parser("verify", help="check the tree against the snapshot and allow-lists")
    ver.add_argument("--scope-root", required=True, type=Path)
    ver.add_argument("--before", required=True, type=Path)
    ver.add_argument("--allow", action="append", default=[], metavar="NAME=PATTERNS")
    ver.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            args.out.write_text(
                json.dumps(_tree(args.scope_root), indent=1, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            print(f"snapshot {args.out}")
            return 0
        allow = parse_allow(args.allow)
        before = json.loads(args.before.read_text(encoding="utf-8"))
        if not isinstance(before, dict):
            raise ValueError("--before is not a snapshot file")
        result = compare(before, _tree(args.scope_root), allow)
        sys.stdout.write(json.dumps(result, indent=1) + "\n" if args.json else _report(result))
        return 0 if result["ok"] else 1
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
