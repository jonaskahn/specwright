#!/usr/bin/env python3
"""Preview or confirm one local lifecycle transition. No remote writes.

Exit codes: 0 preview/applied, 2 blocked/invalid input, 3 ambiguous scope.
"""

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _source_shared if _source_shared.is_dir() else _local_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import graph, lifecycle, workspace  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=sorted(lifecycle.ACTIONS | {"step-back", "reset"}))
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--item", required=True)
    parser.add_argument("--to", choices=["shape", "spec", "review", "plan"])
    parser.add_argument("--destination", choices=["markdown", "jira", "both"])
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, args.item, cwd, True)
        base = workspace.scope_dir(root, scope)
        key = args.item if ":" in args.item else f"{scope}:{args.item}"
        action = args.action
        current = lifecycle.feature(base, key)
        if action == "step-back":
            station = current["station"]
            target = {"publish": "plan", "review": "spec", "spec": "shape", "plan": "spec"}.get(
                station
            )
            if (
                station == "plan"
                and not (base / "03-plan" / f"{key.split(':')[-1]}.tasks.md").exists()
            ):
                target = "review"
        else:
            target = args.to
        if action in ("step-back", "reset"):
            action = {
                "shape": "reopen-shape",
                "spec": "return-spec",
                "review": "return-review",
                "plan": "defer-publish",
            }.get(target)
            if action is None:
                raise ValueError("reset needs an earlier --to station")
        result = lifecycle.transition(
            base, key, action, confirm=args.confirm, destination=args.destination
        )
        if result["applied"]:
            graph.build(root, scope)
        print(json.dumps(result, indent=2))
        return 0
    except workspace.AskUser as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (ValueError, OSError, KeyError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
