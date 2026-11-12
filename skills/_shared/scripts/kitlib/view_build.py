"""Install the console's dependencies and build it, with Node 24 and no shell.

``npm ci`` runs with ``--ignore-scripts`` against the lockfile, a fixed argument list and a
timeout. It runs again only when the lockfile changed since the last install. Both commands
go through ``run`` so a test can replace the process call.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from kitlib import runtime

LOCK_MARK = "node_modules/.specwright-lock"
NPM_CI = ["ci", "--ignore-scripts", "--no-audit", "--no-fund"]
CI_TIMEOUT = 900
BUILD_TIMEOUT = 300

Runner = Callable[..., subprocess.CompletedProcess]


class BuildError(Exception):
    """Node or npm is missing, or a build step failed."""


def npm_command() -> str:
    env = runtime.env_with_node()
    found = shutil.which("npm", path=env["PATH"])
    if not found:
        raise BuildError("npm was not found; Node 24 is required (sh runtime.sh check)")
    return found


def lock_hash(console: Path) -> str:
    lock = console / "package-lock.json"
    if not lock.is_file():
        raise BuildError(f"{lock} is missing")
    return hashlib.sha256(lock.read_bytes()).hexdigest()


def needs_install(console: Path) -> bool:
    mark = console / LOCK_MARK
    return not mark.is_file() or mark.read_text(encoding="utf-8").strip() != lock_hash(console)


def _step(args: list[str], console: Path, timeout: int, run: Runner, label: str) -> None:
    try:
        done = run(
            [npm_command(), *args],
            cwd=console,
            env=runtime.env_with_node(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BuildError(f"{label} failed to run: {exc}") from exc
    if done.returncode != 0:
        tail = "\n".join((done.stderr or done.stdout or "").strip().splitlines()[-8:])
        raise BuildError(f"{label} failed (exit {done.returncode}):\n{tail}")


def build(console: Path, run: Runner = subprocess.run, force: bool = False) -> list[str]:
    """Install if needed, then build; returns what was done."""
    done: list[str] = []
    if force or needs_install(console):
        _step(NPM_CI, console, CI_TIMEOUT, run, "npm ci")
        (console / LOCK_MARK).parent.mkdir(parents=True, exist_ok=True)
        (console / LOCK_MARK).write_text(lock_hash(console) + "\n", encoding="utf-8")
        done.append("npm ci")
    _step(["run", "build"], console, BUILD_TIMEOUT, run, "npm run build")
    done.append("npm run build")
    if not (console / "dist" / "index.html").is_file():
        raise BuildError("the build produced no dist/index.html")
    return done
