#!/usr/bin/env python3
"""Save a quoted proposed impact, not an approved change or requirement revision.

Exit codes: 0 proposal saved, 2 invalid evidence, 3 scope choice required.
"""

import argparse
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

from kitlib import graph, ingest_impact, workspace  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--source", required=True)
    parser.add_argument("--item", required=True)
    parser.add_argument("--source-quote", required=True)
    parser.add_argument("--claim-quote", required=True)
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, args.item, cwd, True)
        path = ingest_impact.propose(
            workspace.scope_dir(root, scope),
            args.source,
            args.item,
            args.source_quote,
            args.claim_quote,
        )
        graph.build(root, scope)
        print(path)
        return 0
    except workspace.AskUser as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
