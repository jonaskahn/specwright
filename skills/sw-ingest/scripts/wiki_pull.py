#!/usr/bin/env python3
"""Read a wiki page tree (read-only) into files and an import list for bulk_import.py.

Configure with SPECWRIGHT_WIKI_SITE (an https origin), SPECWRIGHT_WIKI_EMAIL and
SPECWRIGHT_WIKI_TOKEN. Only GET requests are made; nothing is written to the wiki. Output goes to
_meta/work/pull-<batch>/: one file per page (and per comment with --comments), list.tsv for
bulk_import.py, and pull.json with each page's version, labels, attachments and the counts.

Exit codes: 0 the whole tree was read, 2 invalid configuration or request, 3 the wiki could not be
read, 4 the pull is incomplete (a limit was reached; what was read is still written).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
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

from kitlib import fsio, wiki_rest, workspace  # noqa: E402

COLUMNS = ("path", "title", "source", "source_version", "remote_id", "parent_id", "url", "labels")


def run(args, transport=None):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,40}", args.batch_id):
        raise ValueError("batch id is 1-41 lowercase letters, digits or hyphens")
    cwd = Path(args.cwd).resolve()
    root = workspace.find_root(cwd)
    if root is None:
        raise ValueError("no workspace; run the sw-start workspace setup first")
    scope = workspace.resolve(root, args.scope, None, cwd, True)
    base = workspace.scope_dir(root, scope)
    limits = workspace.load(base / workspace.FLAT_MANIFEST).get("limits") or {}
    max_pages = args.max_pages or int(limits.get("max_pages", 50))
    max_depth = args.depth if args.depth is not None else int(limits.get("child_depth", 2))
    out = base / "_meta" / "work" / f"pull-{args.batch_id}"
    if out.exists():
        raise ValueError(f"{out.name} already exists; use a new batch id")
    client = wiki_rest.Client(transport or wiki_rest.HttpTransport.from_env())
    pull = client.pull_tree(args.root_page, max_pages, max_depth, args.comments)
    rows = wiki_rest.write_pull(pull, out, args.space)
    with (out / "list.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(COLUMNS)
        writer.writerows([[r.get(c, "") for c in COLUMNS] for r in rows])
    detail = {
        "batch_id": args.batch_id,
        "root_page": args.root_page,
        "complete": pull.complete,
        "note": pull.note,
        "received_pages": len(pull.pages),
        "received_files": len(rows),
        "requests": pull.requests,
        "pages": [
            {
                "id": p.id,
                "title": p.title,
                "parent_id": p.parent_id,
                "version": p.version,
                "labels": p.labels,
                "attachments": p.attachments,
                "comments": len(p.comments),
            }
            for p in pull.pages
        ],
    }
    fsio.atomic_write(out / "pull.json", json.dumps(detail, indent=1, sort_keys=True) + "\n")
    summary = {k: v for k, v in detail.items() if k != "pages"}
    summary["next"] = (
        f"bulk_import.py --batch-id {args.batch_id} --list-file {out / 'list.tsv'} "
        f"--expected {len(rows)} --dry-run"
    )
    print(json.dumps(summary, indent=1))
    return 0 if pull.complete else 4


def main(argv=None, transport=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--root-page", required=True, help="numeric ID of the page to start from")
    parser.add_argument("--space", default="wiki", help="space key, used only in the source label")
    parser.add_argument("--max-pages", type=int, help="default: limits.max_pages")
    parser.add_argument("--depth", type=int, help="default: limits.child_depth")
    parser.add_argument("--comments", action="store_true", help="also read comments")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        return run(args, transport)
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except wiki_rest.WikiError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
