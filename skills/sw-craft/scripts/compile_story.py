#!/usr/bin/env python3
"""Compile catalogue features into stories, or propose how to bundle them.

`split` writes `.metadata/work/split-<SRC>.json` and does not create stories.
`compile` writes one already reserved feature from `--legacy` ids in `--from`.

Exit codes: 0 done, 1 the source or the reservation is unusable, 2 usage or workspace error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import compile as compiler  # noqa: E402
from kitlib import ids, workspace  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["split", "compile"])
    parser.add_argument("--scope-root", required=True, type=Path)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--from", dest="source", required=True, help="SRC-0010")
    parser.add_argument("--legacy", help="comma-separated source ids, e.g. F04.06,F04.07")
    parser.add_argument("--feat", help="reserved FEAT-NNN to write")
    parser.add_argument("--epic", help="EPIC-NNN this story belongs to")
    parser.add_argument("--bo", help="BO-NNN the story realizes")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = args.scope_root.resolve()
        if not ids.is_scope(args.scope):
            raise ValueError("scope must be 2..5 uppercase letters")
        base = (
            workspace.scope_dir(root, args.scope) if (root / "workspace.yaml").is_file() else root
        )
        source = ids.find_record(base / "sources", args.source)
        if source is None:
            raise ValueError(f"no snapshot {args.source}")
        if args.command == "split":
            payload = compiler.propose(source.read_text(encoding="utf-8"), args.source)
            target = base / ".metadata/work" / f"split-{args.source}.json"
            text = json.dumps(payload, indent=1) + "\n"
            if args.dry_run:
                print(text, end="")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8", newline="")
                print(target)
            return 0
        if not args.legacy or not args.feat or not args.bo:
            raise ValueError("compile needs --legacy, --feat and --bo")
        legacy = [item.strip() for item in args.legacy.split(",") if item.strip()]
        project = workspace.find_root(base) or root
        target = compiler.write_reserved(
            project,
            args.scope,
            args.source,
            legacy,
            args.feat,
            args.bo,
            args.epic,
            args.dry_run,
        )
        if not args.dry_run:
            print(target)
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
