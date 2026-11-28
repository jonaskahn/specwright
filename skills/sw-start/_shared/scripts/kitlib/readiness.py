"""Delivery status and readiness of epics, features and tasks, calculated from the graph.

A task's status comes from its own `Status:` line. A feature is done when every active task is
done, in progress when any task has started, otherwise todo. An epic follows its features the
same way. An item is blocked while something it `depends_on` is not done, or (for a feature)
while a blocking question is open; blocked is never stored. Ready means todo and not blocked.

The foundation feature of a project is a hard prerequisite too: a feature whose `code:` is not
false waits until the project's foundation is done, because every later task runs `make check`.
A documentation-only feature sets `code: false` and is exempt.
"""

from __future__ import annotations

from kitlib.graph import Graph

TODO, IN_PROGRESS, DONE = "todo", "in_progress", "done"
STATUSES = (TODO, IN_PROGRESS, DONE)
KINDS = ("epic", "feat", "task")
_PROGRESS = {"in-progress": IN_PROGRESS, "done": DONE}
_OUT = {"withdrawn", "superseded"}


def _rollup(children: list[str]) -> str:
    if children and all(c == DONE for c in children):
        return DONE
    return IN_PROGRESS if any(c in (IN_PROGRESS, DONE) for c in children) else TODO


def _foundation(graph: Graph, scope: str) -> str | None:
    """The project's foundation feature: the first feature whose front matter says `kind`."""
    found = [
        k
        for k, n in sorted(graph.nodes.items())
        if n.kind == "feat"
        and n.extra.get("feature_kind") == "foundation"
        and k.startswith(f"{scope}:")
    ]
    return found[0] if found else None


def compute(graph: Graph) -> dict[str, dict]:
    """key -> {kind, status, blocked_by, ready} for every active epic, feature and task."""
    nodes = graph.nodes
    live = {k: n for k, n in nodes.items() if n.kind in KINDS and n.status not in _OUT}
    status: dict[str, str] = {}
    for key, node in live.items():
        if node.kind == "task":
            status[key] = _PROGRESS.get(str(node.extra.get("progress", "")), TODO)
    tasks_of: dict[str, list[str]] = {}
    feats_of: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.rel == "has_task" and e.dst in live:
            tasks_of.setdefault(e.src, []).append(e.dst)
        elif (
            e.rel == "member_of"
            and e.src in live
            and e.dst in live
            and live[e.src].kind == "feat"
            and live[e.dst].kind == "epic"
        ):
            feats_of.setdefault(e.dst, []).append(e.src)
    for key, node in live.items():
        if node.kind == "feat":
            status[key] = _rollup([status[t] for t in tasks_of.get(key, []) if t in status])
    for key, node in live.items():
        if node.kind == "epic":
            status[key] = _rollup([status[f] for f in feats_of.get(key, []) if f in status])
    deps: dict[str, list[str]] = {}
    for e in graph.edges:
        if e.rel == "depends_on" and e.src in live:
            deps.setdefault(e.src, []).append(e.dst)
    out: dict[str, dict] = {}
    foundations = {scope: _foundation(graph, scope) for scope in {k.split(":")[0] for k in live}}
    for key in sorted(live):
        node = live[key]
        blocked = [d for d in sorted(set(deps.get(key, []))) if status.get(d) != DONE]
        scope = key.split(":")[0]
        gate = foundations.get(scope)
        if (
            node.kind == "feat"
            and gate
            and gate != key
            and node.extra.get("code") is not False
            and status.get(gate) != DONE
        ):
            blocked.append(gate)
        blocked += [
            q for q in node.extra.get("lifecycle", {}).get("blocked_by_q", []) if q not in blocked
        ]
        out[key] = {
            "kind": node.kind,
            "status": status[key],
            "blocked_by": blocked,
            "ready": status[key] == TODO and not blocked,
        }
    return out


def newly_ready(before: dict[str, dict], after: dict[str, dict]) -> list[str]:
    """Items that are ready now and were not before: what finishing something opened up."""
    return [
        k for k, v in sorted(after.items()) if v["ready"] and not before.get(k, {}).get("ready")
    ]
