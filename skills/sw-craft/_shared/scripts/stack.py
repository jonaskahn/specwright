#!/usr/bin/env python3
"""Detect, review, lock and enforce a project's technology stack (`stack.yaml`).

    stack.py detect [--write] [--reason TEXT]     propose layers from build files, with evidence
    stack.py show                                 the effective profile (program + project)
    stack.py set <layer>.<field> <value> [--reason TEXT]
    stack.py lib allowed|forbidden|needs_approval <name> [--reason TEXT]
    stack.py convention <text> [--reason TEXT]
    stack.py lock [--confirm sha256:<12>]         preview the hash; lock with that exact hash
    stack.py check --feat FEAT-NNN                tasks against the locked stack

Common: --cwd <project> [--scope SCOPE] [--program] [--format json]. A locked profile changes
only with --reason, which unlocks it and logs the change; lock again afterwards.
Exit codes: 0 ok, 1 check findings, 2 usage, lock or file error, 3 scope ambiguous.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse  # noqa: E402
import json  # noqa: E402

from kitlib import markdown, stack, workspace  # noqa: E402


def _out(data, fmt):
    if fmt == "json":
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(json.dumps(data, indent=2, sort_keys=True) if not isinstance(data, str) else data)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "command", choices=["detect", "show", "set", "lib", "convention", "lock", "check"]
    )
    parser.add_argument("args", nargs="*")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--program", action="store_true", help="edit the program-level profile")
    parser.add_argument("--code", help="folder to scan; default: the project's code folder")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--reason")
    parser.add_argument("--confirm")
    parser.add_argument("--feat")
    parser.add_argument("--format", choices=["text", "json"], default="json")
    a = parser.parse_args(argv)
    try:
        cwd = Path(a.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise stack.StackError("no workspace; run sw-start first")
        scope = (
            None
            if a.program
            else workspace.resolve(
                root, a.scope, a.feat, cwd, a.command not in ("show", "check", "detect") or a.write
            )
        )
        target = stack.path_for(root, scope)
        data = stack.load(target) or stack.empty()

        if a.command == "detect":
            code = (
                Path(a.code).resolve()
                if a.code
                else (workspace.code_root(root, scope) if scope else None) or cwd
            )
            found = stack.detect(code)
            result = {"code": str(code), "proposed": found, "written": False}
            if a.write:
                stack.apply_detected(data, found, a.reason)
                stack.save(target, data)
                result["written"] = str(target)
            _out(result, a.format)
            return 0
        if a.command == "show":
            _out(
                stack.effective(root, scope)
                or {"status": "missing", "hint": "run stack.py detect --write"},
                a.format,
            )
            return 0
        if a.command == "set":
            if len(a.args) != 2:
                raise stack.StackError("usage: set <layer>.<field> <value>")
            stack.set_value(data, a.args[0], a.args[1], a.reason)
        elif a.command == "lib":
            if len(a.args) != 2 or a.args[0] not in ("allowed", "forbidden", "needs_approval"):
                raise stack.StackError("usage: lib allowed|forbidden|needs_approval <name>")
            stack.set_library(data, a.args[0], a.args[1], a.reason)
        elif a.command == "convention":
            if not a.args:
                raise stack.StackError("usage: convention <text>")
            stack.add_convention(data, " ".join(a.args), a.reason)
        elif a.command == "lock":
            result = stack.lock(data, a.confirm)
            if result["applied"]:
                stack.save(target, data)
            else:
                result["next"] = f"after the user's yes: stack.py lock --confirm {result['hash']}"
            _out(result, a.format)
            return 0
        elif a.command == "check":
            if not a.feat:
                raise stack.StackError("check needs --feat FEAT-NNN")
            feat = a.feat.split(":")[-1]
            path = workspace.scope_dir(root, scope) / "03-plan" / f"{feat}.tasks.md"
            if not path.is_file():
                raise stack.StackError(f"no tasks file at {path}")
            blocks = markdown.task_blocks(path.read_text(encoding="utf-8"))
            findings = stack.check_tasks(stack.effective(root, scope), blocks, markdown.task_layer)
            _out({"feat": feat, "findings": findings, "pass": not findings}, a.format)
            return 1 if findings else 0
        stack.save(target, data)
        _out(
            {"saved": str(target), "status": data["status"], "hash": stack.content_hash(data)},
            a.format,
        )
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 3
    except (stack.StackError, OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
