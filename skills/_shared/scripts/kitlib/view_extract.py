"""Unpack the packed console into <spec root>/console without trusting the archive.

The zip is checked against its manifest (sha256 of the zip and of every file) before a byte is
written. Names must be relative, plain and listed in the manifest; links, duplicates and
oversized archives are refused. Files are written through a temporary folder and moved into
place, so a failure leaves the previous console as it was. A console that was changed locally
is never overwritten without ``force``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from kitlib import gitignore

MARKER = ".console-version"
MAX_ENTRIES = 2000
MAX_BYTES = 60 * 1024 * 1024
KEEP = {"node_modules", "dist", ".vite", MARKER, ".gitignore"}


class ExtractError(Exception):
    """The archive does not match its manifest, or the target holds local changes."""


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_manifest(path: Path) -> dict:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ExtractError(f"cannot read the console manifest: {exc}") from exc
    for key in ("files", "tree", "zip", "console"):
        if key not in manifest:
            raise ExtractError(f"the console manifest has no {key}")
    return manifest


def safe_name(name: str) -> PurePosixPath:
    pure = PurePosixPath(name)
    if (
        not name
        or "\\" in name
        or pure.is_absolute()
        or ".." in pure.parts
        or name.startswith("/")
        or (len(name) > 1 and name[1] == ":")
        or name.endswith("/")
    ):
        raise ExtractError(f"unsafe path in the console archive: {name!r}")
    return pure


def verify(zip_path: Path, manifest: dict) -> dict[str, bytes]:
    """The files inside the zip, after every check; raises ExtractError on any mismatch."""
    try:
        raw = zip_path.read_bytes()
    except OSError as exc:
        raise ExtractError(f"cannot read {zip_path}: {exc}") from exc
    if sha(raw) != manifest["zip"]:
        raise ExtractError("console.zip does not match its manifest; reinstall the skill")
    files: dict[str, bytes] = {}
    total = 0
    with zipfile.ZipFile(zip_path) as bundle:
        infos = bundle.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ExtractError("the console archive has too many entries")
        for info in infos:
            safe_name(info.filename)
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or info.is_dir():
                raise ExtractError(f"links and folders are not allowed: {info.filename}")
            if info.filename in files:
                raise ExtractError(f"duplicate entry: {info.filename}")
            total += info.file_size
            if total > MAX_BYTES:
                raise ExtractError("the console archive unpacks to more than expected")
            files[info.filename] = bundle.read(info)
    if {name: sha(data) for name, data in files.items()} != manifest["files"]:
        raise ExtractError("the files in console.zip differ from its manifest")
    return files


def installed(dest: Path) -> dict | None:
    try:
        return json.loads((dest / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def local_changes(dest: Path) -> list[str]:
    """Files that differ from what was installed, or that were added, since the last extract."""
    marker = installed(dest)
    if marker is None:
        mine = dest.is_dir() and any(p.name not in KEEP for p in dest.iterdir())
        return ["(no marker: the folder was not made by sw-view)"] if mine else []
    changed: list[str] = []
    expected: dict[str, str] = marker["files"]
    for name, digest in expected.items():
        path = dest / name
        if not path.is_file() or sha(path.read_bytes()) != digest:
            changed.append(name)
    for path in sorted(dest.rglob("*")):
        rel = path.relative_to(dest)
        if not path.is_file() or rel.parts[0] in KEEP or path.name == ".DS_Store":
            continue
        if rel.as_posix() not in expected:
            changed.append(rel.as_posix())
    return changed


def extract(zip_path: Path, manifest_path: Path, dest: Path, force: bool = False) -> str:
    """'current' when nothing changed, 'extracted' after a fresh install or an upgrade."""
    manifest = load_manifest(manifest_path)
    files = verify(zip_path, manifest)
    marker = installed(dest)
    dirty = local_changes(dest)
    if marker and marker.get("tree") == manifest["tree"] and not dirty:
        return "current"
    if dirty and not force:
        raise ExtractError(
            "the console in "
            + str(dest)
            + " has local changes ("
            + ", ".join(dirty[:5])
            + (" ..." if len(dirty) > 5 else "")
            + "); sw-view will not overwrite them. Use --force to replace them."
        )
    gitignore.ensure_self_ignored(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".console-unpack-") as work:
        staged = Path(work)
        for name, data in files.items():
            target = staged / safe_name(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        if marker:
            for name in marker["files"]:
                if name not in files and (dest / name).is_file():
                    (dest / name).unlink()
        for name in files:
            target = dest / name
            target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged / name, target)
    (dest / MARKER).write_text(
        json.dumps(
            {"console": manifest["console"], "tree": manifest["tree"], "files": manifest["files"]},
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if (dest / "dist").exists() and marker and marker.get("tree") != manifest["tree"]:
        shutil.rmtree(dest / "dist")  # built from the old source
    return "extracted"
