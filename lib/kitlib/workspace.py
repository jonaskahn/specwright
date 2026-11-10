"""Find, create and resolve Specwright workspaces.

A workspace is either flat (one project, manifest at the repo root) or a program (a
workspace manifest listing projects that live under projects/<SCOPE>/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kitlib import fsio, ids, miniyaml, schema, tables

FLAT_MANIFEST = "project.yaml"
PROGRAM_MANIFEST = "workspace.yaml"

EXIT_ERROR = 2
EXIT_ASK = 3


class WorkspaceError(Exception):
    """The workspace is missing, inconsistent or the request is invalid."""


class AskUser(WorkspaceError):
    """The target cannot be chosen safely; the user has to pick."""

    def __init__(self, question: str, options: list[str]) -> None:
        super().__init__(question)
        self.options = options


def load(path: Path) -> dict[str, Any]:
    try:
        return miniyaml.loads(path.read_text(encoding="utf-8"))
    except (OSError, miniyaml.YamlError) as exc:
        raise WorkspaceError(f"cannot read {path}: {exc}") from exc


def find_root(start: Path) -> Path | None:
    """Nearest directory with a manifest; a program manifest wins over nested project files."""
    first_project: Path | None = None
    here = start.resolve()
    for folder in [here, *here.parents]:
        if (folder / PROGRAM_MANIFEST).is_file():
            return folder
        if first_project is None and (folder / FLAT_MANIFEST).is_file():
            first_project = folder
    return first_project


def mode_of(root: Path | None) -> str:
    if root is None:
        return "none"
    return "program" if (root / PROGRAM_MANIFEST).is_file() else "flat"


def list_scopes(root: Path) -> list[str]:
    mode = mode_of(root)
    if mode == "program":
        return [str(s) for s in load(root / PROGRAM_MANIFEST).get("projects") or []]
    if mode == "flat":
        return [str(load(root / FLAT_MANIFEST).get("scope"))]
    return []


def scope_dir(root: Path, scope: str) -> Path:
    return root / "projects" / scope if mode_of(root) == "program" else root


def detect(start: Path) -> dict[str, Any]:
    root = find_root(start)
    return {
        "mode": mode_of(root),
        "root": str(root) if root else None,
        "scopes": list_scopes(root) if root else [],
    }


def _check(root: Path, scope: str) -> str:
    known = list_scopes(root)
    if scope not in known:
        raise WorkspaceError(f"unknown scope '{scope}'; known scopes: {known}")
    return scope


def resolve(
    root: Path,
    arg: str | None = None,
    ref: str | None = None,
    cwd: Path | None = None,
    write: bool = False,
) -> str:
    """Pick the scope: explicit argument, qualified id, path, flat manifest, default, then ask.

    A default is never used for a write, because guessing the wrong project is destructive.
    """
    if arg:
        return _check(root, arg)
    if ref and ":" in ref:
        return _check(root, ref.split(":", 1)[0])
    here = (cwd or Path.cwd()).resolve()
    try:
        parts = here.relative_to(root.resolve()).parts
    except ValueError:
        parts = ()
    if len(parts) >= 2 and parts[0] == "projects":
        return _check(root, parts[1])
    if mode_of(root) == "flat":
        return str(load(root / FLAT_MANIFEST)["scope"])
    manifest = load(root / PROGRAM_MANIFEST)
    default = manifest.get("default_scope")
    if default and not write:
        return _check(root, str(default))
    scopes = list_scopes(root)
    raise AskUser("Which project scope should this run use?", scopes)


def project_manifest(
    scope: str,
    name: str,
    site: str,
    project_key: str,
    epic: str | None,
    approvers: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "name": name,
        "jira": {"site": site, "project_key": project_key, "epic": epic or "None"},
        "status_map": dict(schema.DEFAULT_STATUS_MAP),
        "approvers": approvers,
        "publish": {"transitions": False, "sandbox": True, "attach_diagrams": False},
        "confluence": {"spaces": []},
        "limits": {"child_depth": 2, "max_pages": 50},
    }


def _registry_text() -> str:
    table = tables.Table(list(schema.REGISTRY_COLUMNS))
    return "# ID registry\n\nExternal keys live here and nowhere else.\n\n" + table.render()


def _rtm_text() -> str:
    header = [schema.RTM_ID_COLUMN] + [f"{n} [{o}]" for n, o in schema.RTM_COLUMNS]
    return "# Requirements traceability matrix\n\n" + tables.Table(header).render()


def _write_new(path: Path, text: str, created: list[str], base: Path) -> None:
    if path.exists():
        return
    fsio.atomic_write(path, text)
    created.append(str(path.relative_to(base)))


def init(
    root: Path,
    mode: str,
    scope: str,
    name: str,
    site: str = "TBD",
    project_key: str = "TBD",
    epic: str | None = None,
    approvers: list[dict[str, str]] | None = None,
) -> list[str]:
    """Create the manifests and the folder tree; refuses to overwrite an existing project."""
    if mode not in ("flat", "program"):
        raise WorkspaceError("mode must be 'flat' or 'program'")
    if not ids.is_scope(scope):
        raise WorkspaceError(f"scope must be 2-5 uppercase letters, got '{scope}'")
    existing = mode_of(find_root(root)) if (root / FLAT_MANIFEST).exists() else "none"
    if mode == "flat" and (existing != "none" or (root / PROGRAM_MANIFEST).exists()):
        raise WorkspaceError(f"{root} already holds a workspace manifest")
    root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    manifest = project_manifest(scope, name, site, project_key, epic, approvers or [])
    if mode == "program":
        program_file = root / PROGRAM_MANIFEST
        data = load(program_file) if program_file.exists() else {"mode": "program", "projects": []}
        projects = [str(p) for p in data.get("projects") or []]
        if scope in projects:
            raise WorkspaceError(f"scope '{scope}' already exists in {PROGRAM_MANIFEST}")
        data["projects"] = [*projects, scope]
        data.setdefault("default_scope", scope)
        fsio.atomic_write(program_file, miniyaml.dumps(data))
        created.append(PROGRAM_MANIFEST)
    base = scope_dir(root, scope) if mode == "program" else root
    if mode == "program" and (base / FLAT_MANIFEST).exists():
        raise WorkspaceError(f"{base} already holds a project manifest")
    _write_new(base / FLAT_MANIFEST, miniyaml.dumps(manifest), created, root)
    for folder in schema.SCOPE_DIRS:
        (base / folder).mkdir(parents=True, exist_ok=True)
        _write_new(base / folder / ".gitkeep", "", created, root)
    meta = base / "_meta"
    _write_new(meta / "id-registry.md", _registry_text(), created, root)
    _write_new(meta / "rtm.md", _rtm_text(), created, root)
    _write_new(
        meta / "write-log.md",
        "# Write log\n\nAppend-only. One line per intent and result.\n\n",
        created,
        root,
    )
    return created


def _parse_approver(raw: str) -> dict[str, str]:
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) != 3 or not all(parts):
        raise WorkspaceError(f"approver must be 'role|name|account-id', got '{raw}'")
    return {"role": parts[0], "name": parts[1], "account_id": parts[2]}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Locate, create and resolve Specwright workspaces."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("detect", help="report mode (none/flat/program) and scopes").add_argument(
        "--cwd", default="."
    )
    sub.add_parser("list", help="list scopes").add_argument("--cwd", default=".")
    res = sub.add_parser("resolve", help="print the scope a command should use")
    res.add_argument("--cwd", default=".")
    res.add_argument("--scope")
    res.add_argument("--ref", help="spec id, optionally qualified like REF:FEAT-001")
    res.add_argument("--write", action="store_true", help="never fall back to the default scope")
    init_cmd = sub.add_parser("init", help="create a workspace or add a project to a program")
    init_cmd.add_argument("--root", default=".")
    init_cmd.add_argument("--mode", required=True, choices=["flat", "program"])
    init_cmd.add_argument("--scope", required=True)
    init_cmd.add_argument("--name", required=True)
    init_cmd.add_argument("--jira-site", default="TBD")
    init_cmd.add_argument("--project-key", default="TBD")
    init_cmd.add_argument("--epic")
    init_cmd.add_argument("--approver", action="append", default=[], help="role|name|account-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "init":
            approvers = [_parse_approver(a) for a in args.approver]
            created = init(
                Path(args.root).resolve(),
                args.mode,
                args.scope,
                args.name,
                args.jira_site,
                args.project_key,
                args.epic,
                approvers,
            )
            print("created:\n" + "\n".join(f"  {c}" for c in created))
            return 0
        start = Path(args.cwd).resolve()
        if args.command == "detect":
            print(json.dumps(detect(start), indent=2))
            return 0
        root = find_root(start)
        if root is None:
            raise WorkspaceError("no workspace.yaml or project.yaml found; run init first")
        if args.command == "list":
            print(json.dumps(list_scopes(root)))
            return 0
        print(resolve(root, args.scope, args.ref, start, args.write))
        return 0
    except AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return EXIT_ASK
    except WorkspaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
