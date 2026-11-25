#!/usr/bin/env python3
"""Say what comes after a station: continue to the next skill, confirm, or stop for the user.

Run it as the last step of every station, after maintenance and the checkpoint:

    handoff.py next --cwd <project> [--item FEAT-001] [--done sw-spec] [--until review]

The answer is JSON read from saved files (the lifecycle board), so any skill in any state gets
the same answer. It rebuilds a stale graph (bounded maintenance) and otherwise writes nothing:
no approval, no lifecycle transition, no Jira.

Exit codes: 0 answer printed (read "mode"), 2 usage or unreadable data, 3 scope or item unknown
or ambiguous.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse  # noqa: E402
import json  # noqa: E402

from kitlib import graph, graph_query, handoff, workspace  # noqa: E402

SKILLS = (
    "sw-start",
    "sw-analyze",
    "sw-ingest",
    "sw-shape",
    "sw-spec",
    "sw-review",
    "sw-plan",
    "sw-publish",
)


def _say(answer: dict) -> str:
    """One plain line for the user; the hand-off itself is not a question under flow: auto."""
    mode = answer["mode"]
    if mode == "continue":
        first = " (submitting finished drafts first; not approval)" if answer["transitions"] else ""
        return f"→ {answer['next_skill']} for {', '.join(answer['items']) or 'the scope'}{first}"
    if mode == "confirm":
        return answer["ask"]
    if mode == "done":
        return "Done: story, plan, tasks and agent prompts are delivered as Markdown."
    return "Paused: " + answer["reason"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    nxt = sub.add_parser("next", help="decide the step after a station")
    nxt.add_argument("--cwd", default=".")
    nxt.add_argument("--scope")
    nxt.add_argument("--item", help="named epic or feature; omit for the whole scope")
    nxt.add_argument("--done", choices=SKILLS, help="the skill that just finished")
    nxt.add_argument(
        "--until",
        choices=list(handoff.STATION_ORDER),
        help="the user asked to stop after this station",
    )
    nxt.add_argument("--flow", choices=["auto", "guided", "step"], help="override for this run")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            print(json.dumps({"mode": "stop", "reason": "no workspace; run sw-start"}, indent=2))
            return 0
        scope = workspace.resolve(root, args.scope, args.item, cwd, False)
        store = graph_query.Store(root, scope)
        freshness = store.freshness()
        if freshness == "incompatible":
            answer = {"mode": "stop", "reason": "graph schema is older; sw-start shows the upgrade"}
            print(json.dumps(answer, indent=2))
            return 0
        if freshness != "fresh":
            graph.build(root, scope)
            store = graph_query.Store(root, scope)
        rules = workspace.governance(root, scope)
        flow = args.flow or rules["flow"]
        rows = graph_query.board(store, args.item) if args.item else graph_query.board(store)
        rows = [r for r in rows if r.get("kind") != "epic" or r["condition"] != "complete"]
        rows = handoff.annotate(root, scope, rows)
        answer = handoff.decide(
            rows,
            flow=flow,
            signoff=rules["signoff"],
            done=args.done,
            until=args.until,
            named=bool(args.item),
        )
        answer["scope"] = scope
        answer["say"] = _say(answer)
        print(json.dumps(answer, indent=2, sort_keys=True))
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 3
    except graph_query.QueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except (OSError, ValueError, KeyError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
