"""Commit what a command changed in the spec folder, and push when the repository has a remote.

Run once at the end of a skill command, after its own maintenance (graph, lint, data export). It
stages only the project's spec files, so a person's other work in the same repository is neither
committed nor reordered, and it never forces, never skips a hook and never rewrites history. A
failure is reported in words; the files stay as they are.

The manifest key ``checkpoint`` sets how far it goes: ``push`` (the default), ``commit`` or
``off``. A folder outside git is left alone.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from kitlib import fsio, miniyaml, workspace

MODES = ("off", "commit", "push")
DEFAULT_MODE = "push"
KEY = "checkpoint"
# Rebuilt from the spec on demand, so a commit of them would only add noise.
DERIVED = ("_meta/graph/**", "_meta/data/**", "_meta/work/**", "_meta/lint-report*", "_meta/index*")
BUSY = ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
SUBJECT_MAX = 72
PUSH_SECONDS = 60


@dataclass
class Result:
    #: off, no-repo, nothing, committed, busy, blocked
    status: str
    detail: str = ""
    commit: str = ""
    #: True pushed, False push failed, None not attempted
    pushed: bool | None = None
    where: str = ""

    @property
    def exit_code(self) -> int:
        if self.status == "blocked" or self.status == "busy":
            return 3
        if self.status == "committed" and self.pushed is False:
            return 4
        return 0

    def line(self) -> str:
        if self.status == "committed":
            tail = {True: f"pushed to {self.where}", False: f"push failed: {self.detail}"}.get(
                self.pushed, self.detail or "no remote"
            )
            return f"checkpoint: committed {self.commit} · {tail}"
        return f"checkpoint: {self.status}" + (f" · {self.detail}" if self.detail else "")


def mode_of(manifest: dict) -> str | None:
    value = manifest.get(KEY)
    return str(value) if value in MODES else None


def mode_for(root: Path, scope: str | None) -> str:
    """The project's setting, else the program's, else the default."""
    manifests = []
    if scope:
        manifests.append(workspace.scope_dir(root, scope) / workspace.FLAT_MANIFEST)
    manifests.append(root / workspace.PROGRAM_MANIFEST)
    manifests.append(root / workspace.FLAT_MANIFEST)
    for path in manifests:
        if path.is_file():
            found = mode_of(workspace.load(path))
            if found:
                return found
    return DEFAULT_MODE


def set_mode(root: Path, scope: str | None, value: str) -> str:
    if value not in MODES:
        raise workspace.WorkspaceError(f"{KEY} must be one of {list(MODES)}")
    if scope:
        path = workspace.scope_dir(root, scope) / workspace.FLAT_MANIFEST
    else:
        path = root / (
            workspace.PROGRAM_MANIFEST
            if (root / workspace.PROGRAM_MANIFEST).is_file()
            else workspace.FLAT_MANIFEST
        )
    data = workspace.load(path)
    data[KEY] = value
    fsio.atomic_write(path, miniyaml.dumps(data))
    return value


def _git(top: Path, *args: str, seconds: int = 30) -> subprocess.CompletedProcess[str]:
    exe = shutil.which("git")
    if exe is None:
        return subprocess.CompletedProcess(args, 127, "", "git is not installed")
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return subprocess.run(
            [exe, "-C", str(top), *args],
            capture_output=True,
            text=True,
            timeout=seconds,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"timed out after {seconds}s")
    except OSError as exc:
        return subprocess.CompletedProcess(args, 126, "", str(exc))


def _reason(done: subprocess.CompletedProcess[str]) -> str:
    lines = [ln.strip() for ln in (done.stderr or done.stdout or "").splitlines() if ln.strip()]
    useful = [ln for ln in lines if not ln.startswith(("hint:", "To "))]
    return (useful or lines or [f"git exited {done.returncode}"])[-1][:200]


def _top(folder: Path) -> Path | None:
    done = _git(folder, "rev-parse", "--show-toplevel")
    return Path(done.stdout.strip()).resolve() if done.returncode == 0 else None


def _paths(top: Path, root: Path, scope: str | None) -> list[str]:
    """Pathspecs, relative to the repository, for the project and its manifests."""
    base = workspace.scope_dir(root, scope) if scope else root
    wanted = [base]
    if scope and (root / workspace.PROGRAM_MANIFEST).is_file():
        wanted.append(root / workspace.PROGRAM_MANIFEST)
    specs = [str(p.resolve().relative_to(top)) or "." for p in wanted if p.exists()]
    prefix = str(base.resolve().relative_to(top))
    skip = [f":(exclude,glob){(prefix + '/' if prefix != '.' else '')}{d}" for d in DERIVED]
    return [*specs, *skip]


def _busy(top: Path) -> str | None:
    done = _git(top, "rev-parse", "--git-dir")
    if done.returncode != 0:
        return None
    gitdir = Path(done.stdout.strip())
    gitdir = gitdir if gitdir.is_absolute() else top / gitdir
    return next((name for name in BUSY if (gitdir / name).exists()), None)


def _subject(skill: str, subject: str) -> str:
    text = f"{skill}: {' '.join(subject.split())}".strip()
    return text if len(text) <= SUBJECT_MAX else text[: SUBJECT_MAX - 1].rstrip() + "…"


def _push(top: Path) -> tuple[bool | None, str, str]:
    branch = _git(top, "symbolic-ref", "--short", "-q", "HEAD")
    if branch.returncode != 0:
        return None, "detached HEAD, nothing pushed", ""
    name = branch.stdout.strip()
    upstream = _git(top, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if upstream.returncode == 0:
        target = upstream.stdout.strip()
        done = _git(top, "push", seconds=PUSH_SECONDS)
    else:
        remotes = _git(top, "remote").stdout.split()
        if not remotes:
            return None, "no remote", ""
        remote = "origin" if "origin" in remotes else remotes[0]
        target = f"{remote}/{name}"
        done = _git(top, "push", "-u", remote, name, seconds=PUSH_SECONDS)
    if done.returncode != 0:
        return False, _reason(done), target
    return True, "", target


def commit(
    root: Path,
    scope: str | None,
    skill: str,
    subject: str,
    mode: str | None = None,
) -> Result:
    """Commit the project's spec changes; push when the mode and the repository allow it."""
    chosen = mode or mode_for(root, scope)
    if chosen == "off":
        return Result("off", "set with: checkpoint.py mode --set commit")
    top = _top(root)
    if top is None:
        return Result("no-repo", "the spec folder is not in a git repository")
    action = _busy(top)
    if action:
        return Result("busy", f"{action} is in progress; finish it, then run checkpoint again")
    specs = _paths(top, root, scope)
    changed = _git(top, "status", "--porcelain", "--", *specs)
    if changed.returncode != 0:
        return Result("blocked", _reason(changed))
    if not changed.stdout.strip():
        return Result("nothing", "no spec file changed")
    added = _git(top, "add", "-A", "--", *specs)
    if added.returncode != 0:
        return Result("blocked", _reason(added))
    done = _git(top, "commit", "-q", "-m", _subject(skill, subject), "--", *specs)
    if done.returncode != 0:
        return Result("blocked", _reason(done))
    sha = _git(top, "rev-parse", "--short", "HEAD").stdout.strip()
    if chosen != "push":
        return Result("committed", "push is off", sha)
    pushed, detail, where = _push(top)
    return Result("committed", detail, sha, pushed, where)
