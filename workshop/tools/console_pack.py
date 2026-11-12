#!/usr/bin/env python3
"""Pack the console project into the sw-view skill: one zip and one manifest.

The zip holds the console source (not node_modules, dist or caches) plus the data contract
generated from kitlib/dataformat.py. It is stored, not compressed, so its bytes do not depend
on the zlib version of whoever packs it. The manifest records the sha256 of every file, a hash
of the whole tree and the sha256 of the zip. sw-view checks the zip against the manifest before
it unpacks anything; this tool's --check (run by lint and CI) needs no Node and fails when the
committed zip no longer matches the current source.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE = ROOT / "console"
ASSETS = ROOT / "skills" / "sw-view" / "assets"
ZIP = ASSETS / "console.zip"
MANIFEST = ASSETS / "console.manifest.json"
SKIP_DIRS = {"node_modules", "dist", ".vite", "coverage", "contract", "__pycache__"}
SKIP_FILES = {".DS_Store"}
STAMP = (2020, 1, 1, 0, 0, 0)

sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))
from kitlib import dataformat  # noqa: E402


def _contract() -> dict[str, bytes]:
    spec = importlib.util.spec_from_file_location(
        "gen_contract", ROOT / "workshop/tools/gen_console_contract.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        "contract/types.ts": module.typescript().encode("utf-8"),
        "contract/console-data.schema.json": (
            json.dumps(module.json_schema(), indent=1) + "\n"
        ).encode("utf-8"),
    }


def tree() -> dict[str, bytes]:
    """Every file that ships, by name, in sorted order."""
    files: dict[str, bytes] = {}
    for path in sorted(CONSOLE.rglob("*")):
        rel = path.relative_to(CONSOLE)
        if not path.is_file() or path.name in SKIP_FILES or SKIP_DIRS & set(rel.parts):
            continue
        files[rel.as_posix()] = path.read_bytes()
    files.update(_contract())
    return dict(sorted(files.items()))


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def tree_hash(hashes: dict[str, str]) -> str:
    return sha(
        "".join(f"{name} {digest}\n" for name, digest in sorted(hashes.items())).encode("utf-8")
    )


def build_zip(files: dict[str, bytes]) -> bytes:
    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def manifest_for(files: dict[str, bytes], archive: bytes) -> dict:
    hashes = {name: sha(data) for name, data in files.items()}
    package = json.loads(files["package.json"])
    return {
        "console": package["version"],
        "formatVersion": dataformat.FORMAT_VERSION,
        "files": hashes,
        "tree": tree_hash(hashes),
        "zip": sha(archive),
        "bytes": len(archive),
    }


def render(manifest: dict) -> str:
    return json.dumps(manifest, indent=1, sort_keys=True) + "\n"


def check() -> list[str]:
    """What is wrong with the committed zip; empty when it matches the current source."""
    problems: list[str] = []
    if not ZIP.is_file() or not MANIFEST.is_file():
        return [
            f"{ZIP.relative_to(ROOT)} or its manifest is missing: "
            "run workshop/tools/console_pack.py"
        ]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    archive = ZIP.read_bytes()
    if sha(archive) != manifest["zip"]:
        problems.append("console.zip does not match console.manifest.json")
    with zipfile.ZipFile(ZIP) as bundle:
        packed = {info.filename: sha(bundle.read(info)) for info in bundle.infolist()}
    if packed != manifest["files"]:
        problems.append("the files inside console.zip differ from the manifest")
    current = {name: sha(data) for name, data in tree().items()}
    if current != packed:
        changed = sorted(
            n for n in current.keys() | packed.keys() if current.get(n) != packed.get(n)
        )
        problems.append(
            "console.zip is stale; run workshop/tools/console_pack.py. Differs: "
            + ", ".join(changed[:6])
        )
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the zip is not current")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for line in problems:
            print(line, file=sys.stderr)
        return 1 if problems else 0
    files = tree()
    archive = build_zip(files)
    ASSETS.mkdir(parents=True, exist_ok=True)
    ZIP.write_bytes(archive)
    MANIFEST.write_text(render(manifest_for(files, archive)), encoding="utf-8")
    print(f"packed {len(files)} files, {len(archive)} bytes: {ZIP.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
