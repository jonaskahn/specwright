#!/usr/bin/env python3
"""Query the knowledge graph without reading all of it.

Only 'build' writes. Every list is paged (--limit, --offset) and every answer starts with the
graph freshness. Exit codes: 0 ok, 1 check findings, 2 usage or unreadable data,
3 scope or ID unknown or ambiguous (candidates are listed), 4 stale under --strict.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import dataformat, graph, graph_query, workspace  # noqa: E402

EXIT_FINDINGS, EXIT_ERROR, EXIT_ASK, EXIT_STALE = 1, 2, 3, 4


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text, ident=False, ident2=False):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope", help="project scope; omit at a program root for all")
        cmd.add_argument("--format", choices=["text", "json"], default="text")
        cmd.add_argument("--strict", action="store_true", help="exit 4 when the graph is stale")
        if ident:
            cmd.add_argument("id")
        if ident2:
            cmd.add_argument("other")
        if name in ("neighbors", "up", "down", "find"):
            cmd.add_argument("--limit", type=int, default=graph_query.DEFAULT_LIMIT)
            cmd.add_argument("--offset", type=int, default=0)
        return cmd

    add("map", "print the knowledge map").add_argument("--epic")
    brd = add("board", "per-feature lifecycle board")
    brd.add_argument("--item")
    brd.add_argument("--station")
    add("show", "one node by ID, alias or title, with its crosswalk row", ident=True)
    nb = add("neighbors", "paged links with file and line", ident=True)
    nb.add_argument("--dir", choices=["in", "out", "both"], default="both")
    nb.add_argument("--rel")
    nb.add_argument("--declared-only", action="store_true")
    add("up", "ancestors", ident=True)
    add("down", "descendants", ident=True).add_argument("--depth", type=int, default=2)
    add("path", "shortest connection", ident=True, ident2=True).add_argument(
        "--max", type=int, default=6
    )
    add("impact", "what a change reaches", ident=True)
    ctx = add("context", "files to read for an item", ident=True)
    ctx.add_argument("--with-text", action="store_true")
    ctx.add_argument("--budget", type=int, default=4000)
    fnd = add("find", "filter the index by ID, title or any alias")
    fnd.add_argument("text", nargs="?")
    fnd.add_argument("--kind")
    fnd.add_argument("--status")
    fnd.add_argument("--jira")
    fnd.add_argument("--epic")
    add("build", "rebuild the graph (the only command that writes)")
    add("check", "drift, unresolved links, tombstones, duplicate Jira keys")
    add("stats", "counts")
    return parser


def _store(args, write):
    cwd = Path(args.cwd).resolve()
    root = workspace.find_root(cwd)
    if root is None:
        raise graph_query.QueryError("no workspace; run the sw-start workspace setup first", 2)
    scope = args.scope
    if scope is None and workspace.mode_of(root) == "flat":
        scope = workspace.list_scopes(root)[0]
    ref = getattr(args, "id", None)
    if scope is None and ref and ":" in ref:
        scope = ref.split(":", 1)[0]
    if scope is None and workspace.mode_of(root) == "program" and not write:
        # Reads at a program root use the merged graph; a path inside a project narrows it.
        try:
            scope = workspace.resolve(root, None, None, cwd, True)
        except workspace.AskUser:
            scope = None
    if scope is not None:
        workspace.resolve(root, scope, None, cwd, write)
    return root, scope, graph_query.Store(root, scope)


def _emit(args, store, lines, extra=None):
    if args.format == "json":
        print(json.dumps({"graph": store.freshness(), "lines": lines, **(extra or {})}, indent=1))
    else:
        print(graph_query.header(store))
        print("\n".join(lines))
    return EXIT_STALE if args.strict and store.freshness() != "fresh" else 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "build":
            root = workspace.find_root(Path(args.cwd).resolve())
            if root is None:
                raise graph_query.QueryError(
                    "no workspace; run the sw-start workspace setup first", 2
                )
            scope = (
                workspace.resolve(root, args.scope, None, Path(args.cwd).resolve(), True)
                if (args.scope or workspace.mode_of(root) == "flat")
                else None
            )
            changed = graph.build(root, scope)
            dataformat.refresh(root, "graph", scope)
            print(f"graph built: {len(changed)} file(s) changed")
            for line in graph.drift_warnings(root, scope):
                print(f"warning: {line}", file=sys.stderr)
            return 0
        root, scope, store = _store(args, False)
        if args.command == "check":
            findings = graph.check(root, scope)
            print("\n".join(findings) if findings else "graph clean")
            return EXIT_FINDINGS if findings else 0
        if args.command == "map":
            text = graph_query.read_map(store, args.epic)
            print(graph_query.header(store))
            print(text, end="")
            return EXIT_STALE if args.strict and store.freshness() != "fresh" else 0
        if args.command == "board":
            rows = graph_query.board(store, args.item, args.station)
            lines = [f"{r['id']}: {r['station']} ({r['condition']})" for r in rows]
            return _emit(args, store, lines, {"items": rows})
        if args.command == "stats":
            return _emit(args, store, graph_query.stats(store))
        if args.command == "find":
            lines = graph_query.find(
                store,
                args.text,
                args.kind,
                args.status,
                args.jira,
                args.epic,
                args.offset,
                args.limit,
            )
            return _emit(args, store, lines)
        key = store.resolve(args.id, fuzzy=args.command == "show")
        if args.command == "show":
            return _emit(args, store, graph_query.show(store, key))
        if args.command == "neighbors":
            lines = graph_query.neighbors(
                store, key, args.dir, args.rel, args.declared_only, args.offset, args.limit
            )
            return _emit(args, store, lines)
        if args.command == "up":
            return _emit(args, store, graph_query.up(store, key, args.offset, args.limit))
        if args.command == "down":
            return _emit(
                args, store, graph_query.down(store, key, args.depth, args.offset, args.limit)
            )
        if args.command == "path":
            other = store.resolve(args.other)
            return _emit(args, store, graph_query.path(store, key, other, args.max))
        if args.command == "impact":
            result = graph_query.impact(store, key)
            lines = [f"{name}: {', '.join(values) or 'none'}" for name, values in result.items()]
            return _emit(args, store, lines, {"impact": result})
        if args.command == "context":
            lines = graph_query.context(store, key, args.with_text, args.budget)
            return _emit(args, store, lines)
        return EXIT_ERROR
    except graph_query.QueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        for option in exc.options:
            print(f"  candidate: {option}", file=sys.stderr)
        return exc.code
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return EXIT_ASK
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
