"""Detect an incomplete or mixed skill install before any script trusts its shared files.

Each installed skill carries ``_shared/MANIFEST.json``: the kit version and a short hash of
every shared file. A missing file, a changed file or a version that differs from the code that
is running means the folder was copied piecemeal or from two releases.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from kitlib import schema

MANIFEST = "MANIFEST.json"
REINSTALL = (
    "reinstall every sw-* skill together: npx skills add jonaskahn/specwright "
    "(or rerun install.sh / install.ps1)"
)


def digest(path: Path) -> str:
    """Short content hash that ignores line-ending conversion done by checkouts."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:12]


def manifest_for(files: dict[str, Path]) -> str:
    """Manifest text for ``{relative name: file}``; sorted so it is reproducible."""
    body = {
        "kit_version": schema.KIT_VERSION,
        "files": {rel: digest(path) for rel, path in sorted(files.items())},
    }
    return json.dumps(body, indent=1, sort_keys=True) + "\n"


def folder_files(folder: Path) -> dict[str, Path]:
    return {
        p.relative_to(folder).as_posix(): p
        for p in sorted(folder.rglob("*"))
        if p.is_file() and p.name != MANIFEST and "__pycache__" not in p.parts
    }


def check(skill_dir: Path) -> list[str]:
    """Problems with a skill's own ``_shared`` folder; empty when whole or run from source."""
    shared = skill_dir / "_shared"
    if not shared.is_dir():
        return []  # a source checkout reads the sibling skills/_shared instead
    manifest = shared / MANIFEST
    if not manifest.is_file():
        return [f"_shared/{MANIFEST} is missing"]
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        listed = dict(data["files"])
        version = str(data["kit_version"])
    except (OSError, ValueError, KeyError, TypeError):
        return [f"_shared/{MANIFEST} is unreadable"]
    problems = []
    if version != schema.KIT_VERSION:
        problems.append(
            f"skill files are from kit {version} but its code is kit {schema.KIT_VERSION}"
        )
    for rel, wanted in sorted(listed.items()):
        target = shared / rel
        if not target.is_file():
            problems.append(f"_shared/{rel} is missing")
        elif digest(target) != wanted:
            problems.append(f"_shared/{rel} differs from the release")
    return problems


def explain(problems: list[str]) -> str:
    shown = "; ".join(problems[:5]) + (
        f"; and {len(problems) - 5} more" if len(problems) > 5 else ""
    )
    return f"error: incomplete or mixed install ({shown}). {REINSTALL}"
