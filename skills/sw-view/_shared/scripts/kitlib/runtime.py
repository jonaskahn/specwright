"""Find Python and Node 24 for the tools that already run on Python.

Installing is not here. The first check and every install run from ``scripts/runtime.sh`` (or
``runtime.ps1`` on Windows), because a check written in Python cannot report that Python is
missing. This module only locates the Node folder that script installed under
``~/.specwright/runtime/`` (or any Node on PATH) so the console build can run npm.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
NODE_MAJOR = 24


def runtime_home() -> Path:
    base = os.environ.get("SPECWRIGHT_HOME")
    return (Path(base) if base else Path.home() / ".specwright") / "runtime"


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
