"""Keep generated folders out of git without touching the repository's own .gitignore.

A folder the kit generates (``_meta/data``, ``console``) gets a ``.gitignore`` holding ``*``. A
``*`` file ignores itself too, so git sees nothing in the folder: no stray file, no empty tracked
folder. The file is written only when the folder is created, so a team that wants the folder in
git deletes that one file and it stays deleted. The checks here only read git; they never run
``git add`` or ``git rm``.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

SELF_IGNORE = "*\n"


def ensure_self_ignored(folder: Path) -> bool:
    """Create ``folder`` with a self-ignoring ``.gitignore``; True when it was created now."""
    if folder.exists():
        return False
    folder.mkdir(parents=True)
    (folder / ".gitignore").write_text(SELF_IGNORE, encoding="utf-8")
    return True


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    exe = shutil.which("git")
    if exe is None:
        return None
    try:
        return subprocess.run(
            [exe, "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def repo_top(start: Path) -> Path | None:
    """The git work tree holding ``start``, or None outside git (or without git)."""
    done = _git(start, "rev-parse", "--show-toplevel")
    if done is None or done.returncode != 0:
        return None
    return Path(done.stdout.strip())


def git_findings(folder: Path, probes: list[str]) -> list[str]:
    """Warnings when a generated folder is tracked or not ignored; empty outside git.

    ``probes`` are paths relative to ``folder`` that exist (or would) inside it. Each warning
    carries the command for the user to run; nothing is run here.
    """
    if not folder.is_dir() or repo_top(folder) is None:
        return []
    findings: list[str] = []
    tracked = _git(folder, "ls-files", "--", ".")
    if tracked is not None and tracked.stdout.strip():
        findings.append(
            f"{folder} has tracked files; stop tracking them with: git rm -r --cached {folder}"
        )
    for probe in probes:
        done = _git(folder, "check-ignore", "-q", "--", str(folder / probe))
        if done is not None and done.returncode == 1:
            findings.append(
                f"{folder / probe} is not git-ignored; add a `*` .gitignore to {folder}"
            )
    return findings
