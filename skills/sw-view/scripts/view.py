#!/usr/bin/env python3
"""Open the Specwright console: unpack it, build it, and serve it on this machine.

The console is a read-only dashboard over the data files in _meta/data. `prepare` unpacks the
packed console into <spec root>/console, builds it with Node 24, and prints the command that
serves it. `serve` runs a loopback-only server. `open` does both. `doctor` reports what is
ready. Nothing here writes the data files, a spec, Jira or Confluence.
Exit codes: 0 ok, 1 doctor found a problem, 2 error, 3 a user decision is needed (Node is
missing), 4 data files are missing or stale (reported, not fixed).
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

import argparse
import json
import shutil
import subprocess

from kitlib import (  # noqa: E402
    dataformat,
    gitignore,
    runtime,
    view_build,
    view_extract,
    view_server,
    workspace,
)

SKILL = _here.parent
ZIP = SKILL / "assets" / "console.zip"
MANIFEST = SKILL / "assets" / "console.manifest.json"
EXIT_PROBLEM, EXIT_ERROR, EXIT_DECISION, EXIT_DATA = 1, 2, 3, 4


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("doctor", "report runtimes, the console, and the data files"),
        ("prepare", "unpack and build the console"),
        ("serve", "serve the built console on 127.0.0.1"),
        ("open", "prepare, then serve"),
        ("dev", "run the console's dev server with hot reload"),
    ):
        cmd = sub.add_parser(name, help=text)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--port", type=int, default=4173)
        cmd.add_argument("--format", choices=["text", "json"], default="text")
        cmd.add_argument("--force", action="store_true", help="replace local changes in console/")
        cmd.add_argument(
            "--copy-data",
            action="store_true",
            help="copy the data files into dist/data so a plain static server can show them",
        )
    return parser


def _root(args):
    root = workspace.find_root(Path(args.cwd).resolve())
    if root is None:
        raise ValueError("no workspace; run the sw-start workspace setup first")
    return root


def _console(root: Path) -> Path:
    return root / "console"


def _status(root: Path) -> set[str]:
    """Lines of `git status --porcelain`, empty outside git."""
    if gitignore.repo_top(root) is None:
        return set()
    done = gitignore._git(root, "status", "--porcelain", "--untracked-files=all")
    return set(done.stdout.splitlines()) if done else set()


def _commands(root: Path, port: int) -> dict[str, str]:
    dist = _console(root) / "dist"
    return {
        "serve": f"python3 {Path(__file__).resolve()} serve --cwd {root} --port {port}",
        "plain": f"python3 -m http.server {port} --bind 127.0.0.1 --directory {dist}",
        "url": f"http://127.0.0.1:{port}/",
    }


def _data_findings(root: Path) -> list[dict]:
    return [f for f in dataformat.check(root) if f["status"] != "git"]


def _git_findings(root: Path) -> list[str]:
    return [
        f["message"] for f in dataformat.check(root) if f["status"] == "git"
    ] + gitignore.git_findings(_console(root), ["package.json", "dist/index.html"])


def doctor(args) -> int:
    root = _root(args)
    runtimes = runtime.check()
    report: dict = {"runtime": runtimes}
    try:
        manifest = view_extract.load_manifest(MANIFEST)
        view_extract.verify(ZIP, manifest)
        report["zip"] = f"ok (console {manifest['console']})"
    except view_extract.ExtractError as exc:
        report["zip"] = f"problem: {exc}"
    marker = view_extract.installed(_console(root))
    changes = len(view_extract.local_changes(_console(root)))
    report["console"] = (
        f"installed {marker['console']}; local changes: {changes}" if marker else "not installed"
    )
    report["data"] = [f["message"] for f in _data_findings(root)]
    report["git"] = _git_findings(root)
    if args.format == "json":
        print(json.dumps(report, indent=1))
    else:
        for name, item in runtimes.items():
            print(
                f"{name}: {item['version'] or '-'} ({'ok' if item['ok'] else 'missing or too old'})"
            )
        print(f"console zip: {report['zip']}")
        print(f"console folder: {report['console']}")
        for line in (*report["data"], *report["git"]):
            print(f"note: {line}")
    if report["zip"].startswith("problem") or not runtimes["node"]["ok"]:
        return EXIT_PROBLEM
    return EXIT_DATA if report["data"] else 0


def prepare(args) -> int:
    root = _root(args)
    if not runtime.check()["node"]["ok"]:
        script = Path(runtime.__file__).resolve().parent.parent / "runtime.sh"
        print(
            "Node 24 is needed to build the console. Show the user the plan, and only after "
            f"they approve it run the install:\n  sh {script} plan node"
            f"\n  sh {script} install node --yes"
            "\nOn Windows run runtime.ps1 with `plan node`, then `install node -Yes`.",
            file=sys.stderr,
        )
        return EXIT_DECISION
    before = _status(root)
    notes = [f["message"] for f in _data_findings(root)]
    state = view_extract.extract(ZIP, MANIFEST, _console(root), force=args.force)
    steps = view_build.build(_console(root))
    if args.copy_data:
        target = _console(root) / "dist" / "data"
        target.mkdir(exist_ok=True)
        for path in dataformat.data_dir(root, None).glob("*.json"):
            shutil.copyfile(path, target / path.name)
    commands = _commands(root, args.port)
    added = sorted(_status(root) - before)
    result = {
        "console": state,
        "steps": steps,
        "commands": commands,
        "data_notes": notes,
        "git_added": added,
    }
    if args.format == "json":
        print(json.dumps(result, indent=1))
    else:
        print(f"console {state} in {_console(root)}; {', '.join(steps)}")
        for line in notes:
            print(f"note: {line}")
        print("Serve it with one of:")
        print(f"  {commands['serve']}")
        print(f"  {commands['plain']}   (run prepare with --copy-data first)")
        print(f"Then open {commands['url']}")
    for line in added:
        print(f"warning: prepare changed git status: {line}", file=sys.stderr)
    return (
        EXIT_DATA if notes and not (dataformat.data_dir(root, None) / "index.json").is_file() else 0
    )


def serve(args) -> int:
    root = _root(args)
    dist = _console(root) / "dist"
    if not (dist / "index.html").is_file():
        print(f"error: {dist} is not built; run: view.py prepare --cwd {root}", file=sys.stderr)
        return EXIT_ERROR
    docs = {scope: workspace.scope_dir(root, scope) for scope in workspace.list_scopes(root)}
    server = view_server.make_server(dist, dataformat.data_dir(root, None), args.port, docs=docs)
    port = server.server_address[1]
    print(f"Serving the console on http://127.0.0.1:{port}/ (Ctrl+C stops it)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")
    finally:
        server.server_close()
    return 0


def dev(args) -> int:
    root = _root(args)
    if view_extract.installed(_console(root)) is None:
        print("error: the console is not unpacked; run prepare first", file=sys.stderr)
        return EXIT_ERROR
    env = runtime.env_with_node()
    env["DATA_DIR"] = str(dataformat.data_dir(root, None))
    return subprocess.run(
        [view_build.npm_command(), "run", "dev"], cwd=_console(root), env=env, check=False
    ).returncode


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor(args)
        if args.command == "prepare":
            return prepare(args)
        if args.command == "serve":
            return serve(args)
        if args.command == "dev":
            return dev(args)
        code = prepare(args)
        return serve(args) if code in (0, EXIT_DATA) else code
    except (
        OSError,
        ValueError,
        workspace.WorkspaceError,
        view_extract.ExtractError,
        view_build.BuildError,
        runtime.RuntimeFault,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
