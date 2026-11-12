"""Find Python and Node 24, and install Node into the user's own folder after consent.

Nothing here runs a package manager or touches the system. The installer downloads the one
pinned official archive for the platform, checks its sha256 against ``runtime_pins`` before it
unpacks anything, and unpacks into ``~/.specwright/runtime/``. It does not need administrator
rights and does not change PATH. Without ``yes=True`` it refuses.
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from kitlib import runtime_pins

MIN_PYTHON = (3, 10)
NODE_MAJOR = 24
DOWNLOAD_LIMIT = 120 * 1024 * 1024
UNPACK_LIMIT = 800 * 1024 * 1024


class RuntimeFault(Exception):
    """A missing consent, a bad download or an unsafe archive."""


def runtime_home() -> Path:
    base = os.environ.get("SPECWRIGHT_HOME")
    return (Path(base) if base else Path.home() / ".specwright") / "runtime"


def platform_key() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    system = {"darwin": "darwin", "linux": "linux", "win32": "win"}.get(sys.platform)
    if system is None or (system == "win" and arch != "x64"):
        raise RuntimeFault(f"no pinned Node build for {sys.platform} {machine}")
    return f"{system}-{arch}"


def _version_of(executable: str) -> tuple[int, ...] | None:
    try:
        done = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, timeout=15, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    found = re.match(r"v?(\d+)\.(\d+)\.(\d+)", done.stdout.strip())
    return tuple(int(n) for n in found.groups()) if found else None


def _own_node_dirs() -> list[Path]:
    home = runtime_home()
    return sorted(home.glob("node-v*"), reverse=True) if home.is_dir() else []


def node_bin_dirs() -> list[Path]:
    """Folders that hold node and npm: the ones this kit installed, then those on PATH."""
    out = []
    for folder in _own_node_dirs():
        out.append(folder if sys.platform == "win32" else folder / "bin")
    on_path = shutil.which("node")
    if on_path:
        out.append(Path(on_path).parent)
    return out


def _tool(name: str, folders: list[Path]) -> str | None:
    suffixes = ("", ".exe", ".cmd") if sys.platform == "win32" else ("",)
    for folder in folders:
        for suffix in suffixes:
            candidate = folder / f"{name}{suffix}"
            if candidate.is_file():
                return str(candidate)
    return None


def check() -> dict[str, dict[str, object]]:
    """Python and Node status. Node counts as present only at major version 24 or newer."""
    folders = node_bin_dirs()
    node = _tool("node", folders)
    npm = _tool("npm", folders)
    version = _version_of(node) if node else None
    return {
        "python": {
            "path": sys.executable,
            "version": ".".join(str(n) for n in sys.version_info[:3]),
            "ok": sys.version_info[:2] >= MIN_PYTHON,
            "need": ">=" + ".".join(str(n) for n in MIN_PYTHON),
        },
        "node": {
            "path": node,
            "version": ".".join(str(n) for n in version) if version else None,
            "ok": bool(version and version[0] >= NODE_MAJOR),
            "need": f">={NODE_MAJOR}",
        },
        "npm": {"path": npm, "version": None, "ok": bool(npm), "need": "bundled with Node"},
    }


def env_with_node() -> dict[str, str]:
    """An environment whose PATH starts with the Node folder, for running npm."""
    env = dict(os.environ)
    folders = [str(f) for f in node_bin_dirs()]
    env["PATH"] = os.pathsep.join([*folders, env.get("PATH", "")])
    return env


# ---------------------------------------------------------------------------- install


def pin() -> tuple[str, str, str]:
    """(archive name, sha256, url) for this platform."""
    key = platform_key()
    name, digest = runtime_pins.NODE_PINS[key]
    return name, digest, f"{runtime_pins.NODE_BASE}/{name}"


def target_dir() -> Path:
    name, _, _ = pin()
    return runtime_home() / re.sub(r"\.(tar\.gz|zip)$", "", name)


def plan_node() -> list[str]:
    name, digest, url = pin()
    return [
        f"Install Node {runtime_pins.NODE_VERSION} (the pinned release of Node {NODE_MAJOR}).",
        f"Download:   {url}",
        f"Expect sha256 {digest}; the download is rejected before unpacking if it differs.",
        f"Unpack to:  {target_dir()}",
        "No administrator rights, no PATH change, nothing outside that folder.",
        "To do it yourself instead: `brew install node@24`, `winget install OpenJS.NodeJS`, "
        "or `fnm install 24`.",
    ]


def _download(url: str, fetch: Callable[[str], bytes] | None) -> bytes:
    if not url.startswith("https://nodejs.org/dist/"):
        raise RuntimeFault("refusing a download outside the pinned nodejs.org location")
    if fetch is not None:
        return fetch(url)
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (pinned https URL)
        data = response.read(DOWNLOAD_LIMIT + 1)
    if len(data) > DOWNLOAD_LIMIT:
        raise RuntimeFault("the download is larger than expected")
    return data


def _inside(base: Path, member: PurePosixPath) -> bool:
    if member.is_absolute() or ".." in member.parts:
        return False
    return (base / member).resolve().is_relative_to(base.resolve())


def _unpack_tar(archive: Path, out: Path) -> None:
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        total = 0
        for item in members:
            name = PurePosixPath(item.name)
            if not _inside(out, name):
                raise RuntimeFault(f"unsafe path in the archive: {item.name}")
            if item.issym():
                target = PurePosixPath(os.path.normpath(str(name.parent / item.linkname)))
                if PurePosixPath(item.linkname).is_absolute() or not _inside(out, target):
                    raise RuntimeFault(f"unsafe link in the archive: {item.name}")
            elif not (item.isfile() or item.isdir()):
                raise RuntimeFault(f"unexpected entry type in the archive: {item.name}")
            total += item.size
            if total > UNPACK_LIMIT:
                raise RuntimeFault("the archive unpacks to more than expected")
        tar.extractall(out, members=members)  # noqa: S202 (every member checked above)


def _unpack_zip(archive: Path, out: Path) -> None:
    with zipfile.ZipFile(archive) as bundle:
        total = 0
        for info in bundle.infolist():
            if not _inside(out, PurePosixPath(info.filename.replace("\\", "/"))):
                raise RuntimeFault(f"unsafe path in the archive: {info.filename}")
            total += info.file_size
            if total > UNPACK_LIMIT:
                raise RuntimeFault("the archive unpacks to more than expected")
        bundle.extractall(out)  # noqa: S202 (every member checked above)


def install_node(yes: bool = False, fetch: Callable[[str], bytes] | None = None) -> Path:
    """Install the pinned Node 24 for this user. Returns the folder; refuses without consent."""
    if not yes:
        raise RuntimeFault("installing Node needs the user's approval; run with --yes after it")
    name, digest, url = pin()
    final = target_dir()
    if final.exists():
        return final
    data = _download(url, fetch)
    if hashlib.sha256(data).hexdigest() != digest:
        raise RuntimeFault(f"the download does not match the pinned sha256 for {name}")
    runtime_home().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime_home()) as work:
        archive = Path(work) / name
        archive.write_bytes(data)
        out = Path(work) / "unpacked"
        out.mkdir()
        (_unpack_zip if name.endswith(".zip") else _unpack_tar)(archive, out)
        roots = [p for p in out.iterdir()]
        if len(roots) != 1 or not roots[0].is_dir():
            raise RuntimeFault("the archive does not hold one top-level folder")
        roots[0].rename(final)
    return final
