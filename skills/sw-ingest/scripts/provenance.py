#!/usr/bin/env python3
"""Amend a snapshot's source, version or URL without touching its bytes or its file.

`amend` appends a dated, attributed record to _meta/provenance/<SRC-ID>.jsonl; `show` prints the
effective provenance and its history. The original bytes must still match the snapshot's hash.

Exit codes: 0 done, 2 invalid request or unreadable data, 3 the scope must be chosen.
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
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, ids, provenance, workspace, writelog  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("amend", "show"):
        cmd = sub.add_parser(name)
        cmd.add_argument("snapshot", help="SRC-NNNN")
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope")
        if name == "amend":
            for field in provenance.FIELDS:
                cmd.add_argument("--" + field.replace("_", "-"))
            cmd.add_argument("--by", required=True, help="who amends, e.g. 'BA | An Tran'")
            cmd.add_argument("--reason", required=True)
            cmd.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise provenance.ProvenanceError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, args.command == "amend")
        base = workspace.scope_dir(root, scope)
        src = ids.parse_ref(args.snapshot)
        src_id = src.id if src else args.snapshot
        if args.command == "amend":
            fields = {f: getattr(args, f) for f in provenance.FIELDS}
            target, line = provenance.plan(base, src_id, fields, args.by, args.reason)
            if args.dry_run:
                print(
                    "plan: append to " + target.relative_to(base).as_posix() + "\n  " + line.strip()
                )
                return 0
            with writelog.operation(
                base / "_meta/write-log.md", "sw-ingest", "provenance-amend", f"{scope}:{src_id}"
            ) as op:
                provenance.append(target, line)
                op.wrote(target)
        path = ids.find_record(base / "00-inbox", src_id)
        if path is None:
            raise provenance.ProvenanceError(f"no snapshot {src_id}")
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        merged = provenance.effective(base, src_id, fm)
        print(
            json.dumps(
                {
                    "id": src_id,
                    "effective": {k: merged.get(k, "") for k in provenance.FIELDS},
                    "aliases": merged["aliases"],
                    "amendments": provenance.history(base, src_id),
                },
                indent=1,
            )
        )
        return 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (provenance.ProvenanceError, OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
