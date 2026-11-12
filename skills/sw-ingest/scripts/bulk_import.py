#!/usr/bin/env python3
"""Import many sources in one logged batch with a manifest of what happened to each.

Input is a folder (`--input-dir`) or a tab-separated list (`--list-file`) with a header row and the
columns path, title, source, source_version, remote_id, parent_id, tracker_key, url (only `path` is
required). Parents are imported before children and linked as `source_parent`. The batch writes
00-inbox/imports/<batch-id>/manifest.json with expected and received counts and one status per item.

A batch larger than the project limit (limits.max_pages) runs only with
--confirm-over-limit <count>. --dry-run shows what would be created, including source and
version, and writes nothing.

Exit codes: 0 every item created or already present, 2 invalid request or unreadable input,
3 confirmation needed or an item refused, 4 an item was degraded, 5 expected and received
counts differ.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
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
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import to_md  # noqa: E402

from kitlib import frontmatter, fsio, hashing, ids, provenance, schema, workspace, writelog  # noqa: E402

DEFAULT_LIMIT = 50
BATCH_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")
COLUMNS = (
    "path",
    "title",
    "source",
    "source_version",
    "remote_id",
    "parent_id",
    "tracker_key",
    "url",
)


class BatchError(ValueError):
    """The request is invalid; nothing was written."""


def read_items(input_dir: Path | None, list_file: Path | None) -> list[dict[str, str]]:
    if bool(input_dir) == bool(list_file):
        raise BatchError("give exactly one of --input-dir and --list-file")
    items: list[dict[str, str]] = []
    if input_dir:
        if not input_dir.is_dir():
            raise BatchError(f"{input_dir} is not a folder")
        for path in sorted(p for p in input_dir.rglob("*") if p.is_file() and not p.is_symlink()):
            items.append({"path": str(path)})
        return items
    with list_file.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.reader(handle, delimiter="\t") if r and not r[0].startswith("#")]
    if not rows:
        raise BatchError("the list file is empty")
    header = [h.strip().lower() for h in rows[0]]
    if "path" not in header:
        raise BatchError("the list file needs a header row with a 'path' column")
    for row in rows[1:]:
        item = {name: (row[i].strip() if i < len(row) else "") for i, name in enumerate(header)}
        item = {k: v for k, v in item.items() if k in COLUMNS and v}
        path = Path(item["path"])
        item["path"] = str(path if path.is_absolute() else list_file.resolve().parent / path)
        items.append(item)
    return items


def order_parents_first(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Stable order in which every item follows its parent when the parent is in the batch."""
    by_remote = {i["remote_id"]: i for i in items if i.get("remote_id")}
    placed: list[dict[str, str]] = []
    seen: set[int] = set()

    def place(item: dict[str, str], trail: tuple[int, ...] = ()) -> None:
        if id(item) in seen or id(item) in trail:
            return
        parent = by_remote.get(item.get("parent_id", ""))
        if parent is not None:
            place(parent, (*trail, id(item)))
        seen.add(id(item))
        placed.append(item)

    for item in items:
        place(item)
    return placed


def known_remote_ids(out: Path) -> dict[str, str]:
    """remote ID to SRC ID for snapshots already imported, amendments included."""
    base = out.parent
    found: dict[str, str] = {}
    for path in sorted(out.glob("SRC-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        if fm.get("id"):
            merged = provenance.effective(base, str(fm["id"]), fm)
            if merged.get("remote_id"):
                found[str(merged["remote_id"])] = str(fm["id"])
    return found


def preview(item: dict[str, str], out: Path, planned: str) -> dict:
    path = Path(item["path"])
    if not path.is_file():
        return {"path": item["path"], "status": "missing", "src_id": ""}
    digest = hashing.bytes_hash(path.read_bytes())
    duplicate = ""
    for snapshot in out.glob("SRC-*.md"):
        fm = frontmatter.parse(snapshot.read_text(encoding="utf-8")).fm or {}
        if fm.get("sha256") == digest:
            duplicate = str(fm.get("id"))
    title = item.get("title") or path.stem
    return {
        "path": item["path"],
        "status": "duplicate" if duplicate else "would-create",
        "src_id": duplicate or planned,
        "title": title,
        "source": item.get("source") or path.as_uri(),
        "source_version": item.get("source_version") or "inferred at import",
        "remote_id": item.get("remote_id", ""),
        "parent": item.get("parent_id", ""),
        "sha256": digest,
    }


def run_item(item: dict[str, str], out: Path, scope: str, parents: dict[str, str]) -> dict:
    record = {"path": item["path"], "status": "error", "src_id": "", "exit_code": 2}
    try:
        result = to_md.ingest(
            Path(item["path"]),
            out,
            scope=scope,
            source=item.get("source") or None,
            source_version=item.get("source_version") or None,
            title=item.get("title") or None,
            remote_id=item.get("remote_id") or None,
            remote_url=item.get("url") or None,
            tracker_key=item.get("tracker_key") or None,
            source_parent=parents.get(item.get("parent_id", "")),
        )
        degraded = bool(result.get("degraded"))
        record.update(
            status="duplicate"
            if result.get("duplicate")
            else "degraded"
            if degraded
            else "created",
            src_id=str(result.get("id", "")),
            sha256=result.get("sha256", ""),
            exit_code=4 if degraded else 0,
            warnings=result.get("warnings", []),
            content_class=result.get("content_class", ""),
        )
    except to_md.Refused as exc:
        record.update(status="refused", exit_code=3, reason=str(exc))
    except (to_md.MissingTool, OSError, ValueError, RuntimeError) as exc:
        record.update(status="error", exit_code=2, reason=type(exc).__name__)
    for name in ("remote_id", "source_version", "url"):
        if item.get(name):
            record[name] = item[name]
    if item.get("parent_id"):
        record["parent"] = item["parent_id"]
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--list-file", type=Path)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--source-id", help="a source registered in the manifest")
    parser.add_argument("--expected", type=int, help="items the source should hold")
    parser.add_argument("--confirm-over-limit", type=int, metavar="COUNT")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not BATCH_ID.fullmatch(args.batch_id):
            raise BatchError("batch id is 1-41 lowercase letters, digits or hyphens")
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise BatchError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, True)
        base = workspace.scope_dir(root, scope)
        out = base / "00-inbox"
        items = order_parents_first(read_items(args.input_dir, args.list_file))
        manifest = workspace.load(base / workspace.FLAT_MANIFEST)
        limit = int((manifest.get("limits") or {}).get("max_pages", DEFAULT_LIMIT))
        registered = {s.get("id"): s for s in workspace.source_list(root, scope)}
        if args.source_id and args.source_id not in registered:
            raise BatchError(f"source {args.source_id} is not registered (workspace.py source add)")
        source = registered.get(args.source_id, {})
        expected = args.expected if args.expected is not None else source.get("expected_count")
        batch = out / "imports" / args.batch_id
        if batch.exists():
            raise BatchError(f"batch {args.batch_id} already exists; use a new batch id")
        info = {"items": len(items), "limit": limit, "expected": expected}
        if len(items) > limit and args.confirm_over_limit != len(items):
            print(
                json.dumps({**info, "needs": f"--confirm-over-limit {len(items)}"}), file=sys.stdout
            )
            print(
                f"refused: {len(items)} items exceed the limit of {limit}; "
                f"rerun with --confirm-over-limit {len(items)} to proceed",
                file=sys.stderr,
            )
            return 3
        if args.dry_run:
            taken = ids.taken_ids(base)
            planned = []
            for item in items:
                look = preview(item, out, "")
                if look["status"] == "would-create":
                    look["src_id"] = ids.next_id("SRC", taken, width=4)
                    taken.append(look["src_id"])
                planned.append(look)
            print(json.dumps({**info, "dry_run": True, "items": planned}, indent=1))
            return 0
        parents = known_remote_ids(out)
        records = []
        for item in items:
            record = run_item(item, out, scope, parents)
            if item.get("remote_id") and record["src_id"]:
                parents[item["remote_id"]] = record["src_id"]
            records.append(record)
        counts: dict[str, int] = {}
        for record in records:
            counts[record["status"]] = counts.get(record["status"], 0) + 1
        mismatch = expected is not None and int(expected) != len(items)
        summary = {
            "batch_id": args.batch_id,
            "tool": "bulk_import.py",
            "kit_version": schema.KIT_VERSION,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "scope": scope,
            "source_id": args.source_id or "",
            "source": {k: source[k] for k in ("system", "root", "snapshot_date") if k in source},
            "expected_count": expected,
            "received_count": len(items),
            "counts_match": not mismatch,
            "limit": limit,
            "counts": dict(sorted(counts.items())),
            "items": records,
        }
        target = batch / "manifest.json"
        with writelog.operation(
            base / "_meta/write-log.md", "sw-ingest", "bulk-import", f"{scope}:{args.batch_id}"
        ) as op:
            fsio.atomic_write(target, json.dumps(summary, indent=1, sort_keys=True) + "\n")
            op.wrote(target)
        print(json.dumps({k: v for k, v in summary.items() if k != "items"}, indent=1))
        codes = {r["exit_code"] for r in records}
        if 3 in codes:
            return 3
        if 2 in codes:
            return 2
        if mismatch:
            return 5
        return 4 if 4 in codes else 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (BatchError, OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
