#!/usr/bin/env python3
"""Store one user-provided asset and register it without changing spec files.

Exit codes: 0 stored or duplicate, 2 usage or file error, 3 refusal,
4 stored with warnings. The registry is the only file this script writes besides
the asset itself.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import fsio, hashing, ids, schema, tables  # noqa: E402

MAX_BYTES = 50 * 1024 * 1024
SAFE_KINDS = {"figma", "diagram", "mockup", "raw-idea", "document", "image", "other"}


def _next_asset(root: Path) -> str:
    taken: set[str] = set()
    registry = root / "_meta/asset-registry.md"
    if registry.is_file():
        for row in tables.parse(registry.read_text(encoding="utf-8")).table.rows:
            taken.add(row[0])
    for path in sorted((root / "assets").glob("ASSET-*.url")):
        taken.add(path.stem)
    return ids.next_id("ASSET", taken)


def _safe_name(asset_id: str, source: str) -> str:
    name = Path(source).name or "asset"
    stem = "".join(c if c.isalnum() or c in "._-" else "-" for c in name).strip(".-")
    stem = stem[:80] or "asset"
    return f"{asset_id}.{stem}"


def _registry_row(
    asset_id: str, rel: str, kind: str, digest: str, source: str, refs: str, state: str
) -> list[str]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [asset_id, rel, kind, digest, now, source, refs, state]


def _append_registry(root: Path, row: list[str]) -> None:
    path = root / "_meta/asset-registry.md"
    doc = tables.parse(path.read_text(encoding="utf-8"))
    if doc.table.header != list(schema.ASSET_REGISTRY_COLUMNS):
        raise ValueError("asset registry has unexpected columns")
    doc.table.rows.append(row)
    fsio.atomic_write(path, doc.render())


def store(
    root: Path, kind: str, source: str, refs: str = "", out: str | None = None
) -> tuple[str, Path]:
    if not root.is_dir() or not (root / "project.yaml").is_file():
        raise ValueError("root must be an existing, resolved project directory")
    if kind not in SAFE_KINDS:
        raise ValueError(f"kind must be one of {sorted(SAFE_KINDS)}")
    asset_id = _next_asset(root)
    assets = root / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if "://" in source and out is None:
        target = assets / f"{asset_id}.url"
        text = source
    elif kind == "raw-idea" and out is None:
        target = assets / f"{asset_id}.md"
        text = source
    elif out:
        target = assets / f"{asset_id}.{out.lstrip('.') or 'bin'}"
        text = source
    else:
        source_path = Path(source)
        if not source_path.is_file():
            raise ValueError("source must be an existing file when --out is not given")
        size = source_path.stat().st_size
        if size > MAX_BYTES:
            raise ValueError(f"asset exceeds the {MAX_BYTES} byte cap")
        target = assets / _safe_name(asset_id, source)
        shutil.copyfile(source_path, target)
        digest = hashing.file_hash(target)
        row = _registry_row(asset_id, target.name, kind, digest, source_path.name, refs, "captured")
        _append_registry(root, row)
        return asset_id, target
    target.write_text(text, encoding="utf-8")
    digest = hashing.text_hash(text)
    row = _registry_row(asset_id, target.name, kind, digest, source, refs, "captured")
    _append_registry(root, row)
    return asset_id, target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--kind", required=True, choices=sorted(SAFE_KINDS))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source")
    group.add_argument("--text")
    parser.add_argument("--out")
    parser.add_argument("--refs", default="")
    args = parser.parse_args(argv)
    try:
        source = args.text if args.text is not None else args.source
        asset_id, target = store(args.root, args.kind, source, args.refs, args.out)
        print(f"{asset_id} {target.name} stored")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
