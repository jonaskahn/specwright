#!/usr/bin/env python3
"""Save one immutable Jira snapshot through the REST adapter.

Exit codes: 0 saved, 2 invalid input or remote failure, 3 warnings need review.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import jira_port, jira_rest, sync, workspace  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("key")
    parser.add_argument("--root", default=".")
    parser.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        root = Path(args.root).resolve()
        project = workspace.find_root(root) or root
        scope = workspace.resolve(project, args.scope, None, root)
        base = workspace.scope_dir(project, scope)
        port = jira_rest.JiraREST()
        issue, body, warnings = sync.pull(port, args.key)
        text = sync.snapshot_text(issue, body, warnings)
        path = sync.save_snapshot(base, args.key, text)
        print(json.dumps({"snapshot": str(path), "warnings": warnings}))
        return 3 if warnings else 0
    except (OSError, ValueError, jira_port.JiraError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
