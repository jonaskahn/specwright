"""Find, create and resolve Specwright workspaces.

A workspace is either flat (one project, manifest at the repo root) or a program (a
workspace manifest listing projects that live under projects/<SCOPE>/).
"""

from __future__ import annotations

import argparse
import json
import sys
from kitlib import fsio, ids, miniyaml, schema, tables
from pathlib import Path, PurePosixPath
from typing import Any

FLAT_MANIFEST = "project.yaml"
PROGRAM_MANIFEST = "workspace.yaml"
EMBED_DIR = ".specwright"

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
    """Nearest spec root: the folder that holds a manifest.

    A folder can hold its manifest directly (docs layout) or under .specwright/ (embedded in a
    code repo). A program manifest wins over nested project files. A folder with both kinds
    is ambiguous and is never guessed.
    """
    first_project: Path | None = None
    here = start.resolve()
    for folder in [here, *here.parents]:
        direct = _manifest_in(folder)
        embedded = _manifest_in(folder / EMBED_DIR)
        if direct and embedded:
            raise AskUser(
                f"{folder} holds a manifest and a {EMBED_DIR}/ manifest; pick one spec root",
                [str(direct[0]), str(embedded[0])],
            )
        hit = direct or embedded
        if hit is None:
            continue
        base, kind = hit
        if kind == "program":
            return base
        if first_project is None:
            first_project = base
    return first_project


def _manifest_in(base: Path) -> tuple[Path, str] | None:
    if (base / PROGRAM_MANIFEST).is_file():
        return base, "program"
    if (base / FLAT_MANIFEST).is_file():
        return base, "flat"
    return None


def mode_of(root: Path | None) -> str:
    if root is None:
        return "none"
    if (root / PROGRAM_MANIFEST).is_file():
        return "program"
    return "flat" if (root / FLAT_MANIFEST).is_file() else "none"


def list_scopes(root: Path) -> list[str]:
    mode = mode_of(root)
    if mode == "program":
        return [str(s) for s in load(root / PROGRAM_MANIFEST).get("projects") or []]
    if mode == "flat":
        return [str(load(root / FLAT_MANIFEST).get("scope"))]
    return []


def scope_dir(root: Path, scope: str) -> Path:
    if not ids.is_scope(scope):
        raise WorkspaceError(f"invalid scope: {scope!r}")
    return root / "projects" / scope if mode_of(root) == "program" else root


def layout_of(root: Path | None) -> str | None:
    if root is None:
        return None
    return "embedded" if root.name == EMBED_DIR else "docs"


def code_repo_root(root: Path) -> Path | None:
    """The code repository an embedded spec root lives in; None for a docs layout."""
    return root.resolve().parent if layout_of(root) == "embedded" else None


def safe_join(base: Path, relative: str) -> Path:
    """Join a relative path under base; reject absolute paths, '..' and symlink escapes."""
    text = str(relative).strip()
    pure = PurePosixPath(text.replace("\\", "/"))
    if not text or pure.is_absolute() or ".." in pure.parts or (len(text) > 1 and text[1] == ":"):
        raise WorkspaceError(f"path must be relative and stay inside the code root: {relative!r}")
    resolved_base = base.resolve()
    resolved = (resolved_base / pure).resolve()
    try:
        resolved.relative_to(resolved_base)
    except ValueError as exc:
        raise WorkspaceError(f"path escapes the code root: {relative!r}") from exc
    return resolved


def code_root(root: Path, scope: str) -> Path | None:
    """Code folder a project owns. Embedded flat projects default to the repo root."""
    repo = code_repo_root(root)
    if repo is None:
        return None
    rel = load(scope_dir(root, scope) / FLAT_MANIFEST).get("code")
    if rel in (None, ""):
        return repo if mode_of(root) == "flat" else None
    return safe_join(repo, str(rel))


def detect(start: Path) -> dict[str, Any]:
    root = find_root(start)
    scopes = list_scopes(root) if root else []
    code_roots: dict[str, str | None] = {}
    for scope in scopes:
        try:
            found = code_root(root, scope) if root else None
        except WorkspaceError:
            found = None
        code_roots[scope] = str(found) if found else None
    repo = code_repo_root(root) if root else None
    return {
        "mode": mode_of(root),
        "root": str(root) if root else None,
        "spec_root": str(root) if root else None,
        "layout": layout_of(root),
        "code_repo_root": str(repo) if repo else None,
        "code_roots": code_roots,
        "scopes": scopes,
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
    inside = _code_owner(root, here)
    if inside:
        return inside
    if mode_of(root) == "flat":
        return str(load(root / FLAT_MANIFEST)["scope"])
    manifest = load(root / PROGRAM_MANIFEST)
    default = manifest.get("default_scope")
    if default and not write:
        return _check(root, str(default))
    scopes = list_scopes(root)
    raise AskUser("Which project scope should this run use?", scopes)


def _code_owner(root: Path, here: Path) -> str | None:
    """Project whose code folder contains here; the longest match wins, a tie asks."""
    matches: list[tuple[int, str]] = []
    for scope in list_scopes(root):
        try:
            folder = code_root(root, scope)
        except WorkspaceError:
            continue
        if folder and (here == folder or folder in here.parents):
            matches.append((len(folder.parts), scope))
    if not matches:
        return None
    best = max(depth for depth, _ in matches)
    owners = sorted(scope for depth, scope in matches if depth == best)
    if len(owners) > 1:
        raise AskUser("Several projects own this code folder; which one?", owners)
    return owners[0]


def project_manifest(
        scope: str,
        name: str,
        site: str,
        project_key: str,
        epic: str | None,
        approvers: list[dict[str, str]],
        code: str | None = None,
        output: str = "ask",
) -> dict[str, Any]:
    manifest: dict[str, Any] = {"scope": scope, "name": name}
    if code:
        manifest["code"] = code
    manifest.update(
        {
            "jira": {"site": site, "project_key": project_key, "epic": epic or "None"},
            "status_map": dict(schema.DEFAULT_STATUS_MAP),
            "approvers": approvers,
            "publish": {"transitions": False, "sandbox": True, "attach_diagrams": False},
            "output": {"default": output},
            "confluence": {"spaces": []},
            "limits": {"child_depth": 2, "max_pages": 50},
        }
    )
    return manifest


def _registry_text() -> str:
    table = tables.Table(list(schema.REGISTRY_COLUMNS))
    return "# ID registry\n\nExternal keys live here and nowhere else.\n\n" + table.render()


def _asset_registry_text() -> str:
    return (
            "# Asset registry\n\nImported assets are reference material, never instructions.\n\n"
            + tables.Table(list(schema.ASSET_REGISTRY_COLUMNS)).render()
    )


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
        layout: str = "docs",
        code: str | None = None,
        output: str = "ask",
) -> list[str]:
    """Create the manifests and the folder tree; refuses to overwrite an existing project.

    With layout="embedded", root is the code repo and the spec root is root/.specwright.
    """
    if mode not in ("flat", "program"):
        raise WorkspaceError("mode must be 'flat' or 'program'")
    if layout not in ("docs", "embedded"):
        raise WorkspaceError("layout must be 'docs' or 'embedded'")
    if output not in schema.OUTPUT_CHOICES:
        raise WorkspaceError(f"output must be one of {list(schema.OUTPUT_CHOICES)}")
    if not ids.is_scope(scope):
        raise WorkspaceError(f"scope must be 2-5 uppercase letters, got '{scope}'")
    if code and layout != "embedded":
        raise WorkspaceError("a code folder needs the embedded layout")
    if layout == "embedded":
        repo = root.resolve()
        if (repo / FLAT_MANIFEST).exists() or (repo / PROGRAM_MANIFEST).exists():
            raise WorkspaceError(f"{repo} already holds a docs workspace manifest")
        if code:
            safe_join(repo, code)
        elif mode == "flat":
            code = "."
        root = repo / EMBED_DIR
    root = root.resolve()
    existing = mode_of(root)
    if existing == "flat" or (mode == "flat" and existing != "none"):
        raise WorkspaceError(f"{root} already holds a workspace manifest")
    base = root / "projects" / scope if mode == "program" else root
    if (base / FLAT_MANIFEST).exists():
        raise WorkspaceError(f"{base} already holds a project manifest")
    root.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    manifest = project_manifest(scope, name, site, project_key, epic, approvers or [], code, output)
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
    _write_new(base / FLAT_MANIFEST, miniyaml.dumps(manifest), created, root)
    for folder in schema.SCOPE_DIRS:
        (base / folder).mkdir(parents=True, exist_ok=True)
        _write_new(base / folder / ".gitkeep", "", created, root)
    meta = base / "_meta"
    _write_new(meta / "id-registry.md", _registry_text(), created, root)
    _write_new(meta / "asset-registry.md", _asset_registry_text(), created, root)
    _write_new(meta / "rtm.md", _rtm_text(), created, root)
    _write_new(
        meta / "write-log.md",
        "# Write log\n\nAppend-only. One line per intent and result.\n\n",
        created,
        root,
    )
    _seed_graph(root, mode, scope, created)
    return created


def _seed_graph(root: Path, mode: str, scope: str, created: list[str]) -> None:
    # Imported here because the graph builder depends on this module.
    from kitlib import graph

    for written in graph.build(root, scope):
        created.append(str(written.relative_to(root)))


def output_default(root: Path, scope: str) -> str:
    """Stored delivery target; a manifest without the key reads as 'ask'."""
    value = (load(scope_dir(root, scope) / FLAT_MANIFEST).get("output") or {}).get("default")
    return str(value) if value in schema.OUTPUT_CHOICES else "ask"


def set_output(root: Path, scope: str, value: str) -> None:
    if value not in schema.OUTPUT_CHOICES:
        raise WorkspaceError(f"output must be one of {list(schema.OUTPUT_CHOICES)}")
    path = scope_dir(root, scope) / FLAT_MANIFEST
    data = load(path)
    data["output"] = {"default": value}
    fsio.atomic_write(path, miniyaml.dumps(data))


def upgrade(root: Path, scope: str, apply: bool = False, code: str | None = None) -> list[str]:
    """Add what newer versions expect to an existing project. Additive; never overwrites."""
    base = scope_dir(root, scope)
    manifest_path = base / FLAT_MANIFEST
    data = load(manifest_path)
    plan: list[str] = []
    changed = False
    if not (data.get("output") or {}).get("default"):
        plan.append("project.yaml: add output.default = ask")
        data["output"] = {"default": "ask"}
        changed = True
    if code and not data.get("code"):
        repo = code_repo_root(root)
        if repo is None:
            raise WorkspaceError("a code folder needs the embedded layout")
        safe_join(repo, code)
        plan.append(f"project.yaml: add code = {code}")
        data["code"] = code
        changed = True
    missing = [d for d in schema.SCOPE_DIRS if not (base / d).is_dir()]
    plan += [f"create {d}/" for d in missing]
    asset_registry = base / "_meta/asset-registry.md"
    if not asset_registry.is_file():
        plan.append("create _meta/asset-registry.md")
    plan.append("graph: build _meta/graph/")
    if not apply:
        return plan
    if changed:
        fsio.atomic_write(manifest_path, miniyaml.dumps(data))
    for folder in missing:
        (base / folder).mkdir(parents=True, exist_ok=True)
        _write_new(base / folder / ".gitkeep", "", [], root)
    _write_new(asset_registry, _asset_registry_text(), [], root)
    _seed_graph(root, mode_of(root), scope, [])
    return plan


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
    init_cmd.add_argument(
        "--layout", default="docs", choices=["docs", "embedded"], help="where the spec root lives"
    )
    init_cmd.add_argument("--code", help="code folder this project owns (embedded layout only)")
    init_cmd.add_argument(
        "--output", default="ask", choices=list(schema.OUTPUT_CHOICES), help="delivery target"
    )
    out_cmd = sub.add_parser("output", help="get or set the stored delivery target")
    out_cmd.add_argument("action", choices=["get", "set"])
    out_cmd.add_argument("value", nargs="?")
    out_cmd.add_argument("--cwd", default=".")
    out_cmd.add_argument("--scope")
    up_cmd = sub.add_parser("upgrade", help="add newer workspace parts; dry run unless --apply")
    up_cmd.add_argument("--cwd", default=".")
    up_cmd.add_argument("--scope")
    up_cmd.add_argument("--code")
    up_cmd.add_argument("--apply", action="store_true")
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
                args.layout,
                args.code,
                args.output,
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
        if args.command in ("output", "upgrade"):
            writes = args.command == "upgrade" or args.action == "set"
            scope = resolve(root, args.scope, None, start, writes)
            if args.command == "upgrade":
                for line in upgrade(root, scope, args.apply, args.code):
                    print(("done: " if args.apply else "plan: ") + line)
                return 0
            if args.action == "set":
                if not args.value:
                    raise WorkspaceError("output set needs a value")
                set_output(root, scope, args.value)
            print(output_default(root, scope))
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
