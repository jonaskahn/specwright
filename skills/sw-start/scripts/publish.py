#!/usr/bin/env python3
"""Check publication preconditions and render a dry-run plan.

Exit codes: 0 valid, 2 blocked plan or usage. Execution stays an explicit library call.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import jira_diff, publish  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "confirm"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--feat", required=True)
    parser.add_argument("--scope")
    parser.add_argument("--confirm")
    args = parser.parse_args(argv)
    try:
        ctx = publish.context(Path(args.root).resolve(), args.feat, args.scope)
        errors = publish.preconditions(ctx)
        if errors:
            raise publish.PublishError("; ".join(errors))
        draft = ctx.draft.read_text(encoding="utf-8")
        result = jira_diff.plan(
            "",
            "",
            draft,
            scope_id=ctx.scope_id,
            jira_key=publish.registry_key(ctx) or "NEW",
        )
        if args.command == "confirm":
            print(
                json.dumps(
                    {
                        "confirmed": publish.confirmed(args.confirm or "", result),
                        "short_hash": result["short_hash"],
                    }
                )
            )
        else:
            print(jira_diff.render_plan(result), end="")
        return 0
    except (publish.PublishError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
