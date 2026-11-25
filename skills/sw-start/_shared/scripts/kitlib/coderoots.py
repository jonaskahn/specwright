"""Where a project's code lives: inside the spec repo, beside it, or nowhere.

Code is read-only evidence. A project may own several code roots (an API repo and a web repo
beside the spec folder). They are stored in the project manifest as ``code_roots``: a list of
``{name, path}`` with ``path`` relative to the project folder (``..`` allowed, because code
often sits next to the docs). The older single ``code`` key still counts.

``detect`` proposes roots without writing: the repository the workspace is embedded in, and
neighbouring folders that hold build files. Registering them is a separate, confirmed step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kitlib import fsio, miniyaml, workspace

BUILD_MARKERS = (
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "pubspec.yaml",
    "Cargo.toml",
    "composer.json",
    "Gemfile",
)
MAX_CANDIDATES = 6
GENERIC = {
    "api",
    "web",
    "app",
    "docs",
    "doc",
    "spec",
    "specs",
    "service",
    "server",
    "client",
    "frontend",
    "backend",
    "repo",
    "code",
    "src",
    "main",
    "project",
}
SKIP = {".git", "node_modules", ".specwright", ".venv", "venv", "dist", "build", "target"}


def _has_build(folder: Path) -> bool:
    if any((folder / m).is_file() for m in BUILD_MARKERS):
        return True
    if any(folder.glob("*.csproj")) or any(folder.glob("*.sln")):
        return True
    # A monorepo keeps build files one level down (apps/api/pom.xml).
    for child in folder.iterdir() if folder.is_dir() else []:
        if child.is_dir() and child.name not in SKIP:
            if any((child / m).is_file() for m in BUILD_MARKERS):
                return True
    return False


def registered(root: Path, scope: str) -> list[dict[str, Any]]:
    """Code roots the manifest names, resolved; missing folders are reported, not dropped."""
    base = workspace.scope_dir(root, scope)
    manifest = workspace.load(base / workspace.FLAT_MANIFEST)
    out = []
    for entry in manifest.get("code_roots") or []:
        if isinstance(entry, dict) and entry.get("path"):
            path = (base / str(entry["path"])).resolve()
            out.append(
                {
                    "name": str(entry.get("name") or path.name),
                    "path": str(entry["path"]),
                    "abs": str(path),
                    "exists": path.is_dir(),
                }
            )
    if not out:
        legacy = workspace.code_root(root, scope)
        if legacy:
            out.append({"name": legacy.name, "path": "", "abs": str(legacy), "exists": True})
    return out


def detect(root: Path, scope: str) -> list[dict[str, Any]]:
    """Candidate code roots not yet registered: the enclosing repo and build-file neighbours."""
    base = workspace.scope_dir(root, scope).resolve()
    known = {r["abs"] for r in registered(root, scope)}
    found: dict[str, dict[str, Any]] = {}
    repo = workspace.code_repo_root(root)
    if repo and _has_build(repo):
        found[str(repo.resolve())] = {"reason": "the repository this workspace sits in"}
    # Neighbours of the spec folder and of its repository (docs repo beside code repos).
    parents = {base.parent}
    if repo:
        parents.add(repo.resolve().parent)
    for parent in parents:
        try:
            children = sorted(parent.iterdir())
        except OSError:
            continue
        for child in children:
            if (
                child.is_dir()
                and child.name not in SKIP
                and not child.name.startswith(".")
                and child.resolve() != base
                and _has_build(child)
            ):
                found.setdefault(
                    str(child.resolve()), {"reason": "a neighbouring folder with build files"}
                )
    # Rank neighbours by name overlap with the project (shop-docs ↔ shop-api), keep the top few.
    names = {
        base.name,
        base.parent.name,
        str(workspace.load(base / workspace.FLAT_MANIFEST).get("name") or ""),
    }
    if repo:
        names.add(repo.name)
    tokens = {w for n in names for w in _tokens(n)}
    out = []
    known_paths = [Path(k) for k in known]
    for abs_path, info in found.items():
        # Already registered, or a sub-folder of a registered root (api/ inside the repo).
        if abs_path in known or any(k in Path(abs_path).parents for k in known_paths):
            continue
        p = Path(abs_path)
        rel = Path(_relpath(p, base))
        score = 100 if "repository" in info["reason"] else len(_tokens(p.name) & tokens)
        out.append(
            {"name": p.name, "path": rel.as_posix(), "abs": abs_path, "score": score, **info}
        )
    out.sort(key=lambda d: (-d["score"], d["name"]))
    return out[:MAX_CANDIDATES]


def _tokens(name: str) -> set[str]:
    import re

    return {w for w in re.split(r"[^a-z0-9]+", name.lower()) if len(w) >= 3 and w not in GENERIC}


def _relpath(target: Path, start: Path) -> str:
    import os

    return os.path.relpath(target, start)


def register(root: Path, scope: str, paths: list[str]) -> list[dict[str, Any]]:
    """Add code roots (paths relative to the project folder or absolute) to the manifest."""
    base = workspace.scope_dir(root, scope)
    manifest_path = base / workspace.FLAT_MANIFEST
    manifest = workspace.load(manifest_path)
    entries = [e for e in manifest.get("code_roots") or [] if isinstance(e, dict)]
    have = {(base / str(e.get("path", ""))).resolve() for e in entries}
    for raw in paths:
        p = Path(raw)
        p = (p if p.is_absolute() else base / p).resolve()
        if not p.is_dir():
            raise workspace.WorkspaceError(f"not a folder: {raw}")
        if p in have:
            continue
        entries.append({"name": p.name, "path": Path(_relpath(p, base.resolve())).as_posix()})
        have.add(p)
    manifest["code_roots"] = entries
    fsio.atomic_write(manifest_path, miniyaml.dumps(manifest))
    return registered(root, scope)


def all_roots(root: Path, scope: str) -> list[Path]:
    """Existing registered code roots as paths (empty when the project has no code)."""
    return [Path(r["abs"]) for r in registered(root, scope) if r["exists"]]
