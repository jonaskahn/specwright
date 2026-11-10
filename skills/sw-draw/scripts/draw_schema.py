"""Closed, evidence-preserving contracts for structured diagrams."""

from __future__ import annotations

import re
from datetime import date

from draw_common import ParagraphRequired, label, number, refs
from draw_types import CHARTS, GRAPHS, HIERARCHIES, OTHER

LIMITS = dict.fromkeys(GRAPHS + HIERARCHIES + CHARTS + OTHER, 9)
LIMITS.update({"uml-class": 7, "venn": 3, "radar": 5, "polar": 9, "kanban": 12})
NO_EDGES = set(CHARTS) - {"wardley"} | {
    "timeline",
    "gantt",
    "venn",
    "dp-security-matrix",
    "kanban",
    "nested",
    "layer-stack",
    "fishbone",
}
COMMON_NODE = {"id", "label", "spec_ids", "actor"}
EXTRA_NODE = {
    "architecture": {"zone", "kind"},
    "architecture-delta": {"status", "before_label", "after_label"},
    "it-current-state": {"department", "condition"},
    "process": {"input", "output"},
    "data-flow": {"lane", "payload"},
    "dp-integration": {"zone", "protocol"},
    "deployment": {"host", "zone", "replicas"},
    "dependency": {"version"},
    "tree": set(),
    "org-chart": {"role"},
    "nested": {"parent"},
    "layer-stack": {"responsibility"},
    "loop": set(),
    "fishbone": {"category"},
    "timeline": {"date"},
    "gantt": {"start", "end"},
    "quadrant": {"x", "y"},
    "wardley": {"evolution", "visibility"},
    "radar": {"values"},
    "polar": {"value"},
    "pyramid": {"value"},
    "treemap": {"value", "segments"},
    "heatmap": {"row", "column", "value"},
    "bar": {"value", "compare"},
    "waterfall": {"value", "total"},
    "line": {"values"},
    "scatter": {"x", "y", "size", "samples"},
    "venn": {"members"},
    "dp-security-matrix": {"permissions"},
    "sankey": {"stage"},
    "kanban": {"column", "state", "owner"},
    "uml-class": {"attributes", "operations"},
    "db-schema": {"columns"},
}
EXTRA_TOP = {
    "architecture": {"zones"},
    "architecture-delta": {"changes"},
    "quadrant": {"x_axis", "y_axis"},
    "wardley": set(),
    "radar": {"axes", "maximum"},
    "polar": {"unit", "maximum"},
    "pyramid": {"unit", "variant"},
    "treemap": {"unit", "variant"},
    "heatmap": {"rows", "columns", "unit"},
    "bar": {"unit", "variant"},
    "waterfall": {"unit"},
    "line": {"categories", "unit", "variant"},
    "scatter": {"x_axis", "y_axis", "variant"},
    "venn": set(),
    "dp-security-matrix": {"columns"},
    "sankey": {"unit"},
    "fishbone": {"effect"},
    "kanban": {"columns", "limits"},
}
VARIANTS = {
    "bar": {"bar", "dumbbell"},
    "line": {"line", "slopegraph", "ridgeline", "streamgraph", "bump"},
    "scatter": {"scatter", "bubble", "beeswarm", "box-plot"},
    "treemap": {"treemap", "marimekko"},
    "pyramid": {"pyramid", "funnel"},
}
RELATIONS = {
    "association",
    "inheritance",
    "realization",
    "composition",
    "aggregation",
    "dependency",
}


def fields(obj, allowed, context):
    extra = set(obj) - allowed
    if extra:
        raise ValueError(f"{context}: unsupported fields {sorted(extra)}")


def names(value, key, minimum=1, maximum=9):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{key} needs {minimum}..{maximum} labels")
    for item in value:
        label(item, 24)
    if len(set(value)) != len(value):
        raise ValueError(f"{key} labels must be unique")
    return value


def strings(value, key, maximum=5):
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"{key} needs at most {maximum} text rows")
    for row in value:
        label(row, 32)


def iso(value, key):
    label(value, 10)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be an ISO date YYYY-MM-DD") from exc


def tree_parents(spec):
    nodes = spec["nodes"]
    parent = {}
    for edge in spec.get("edges", []):
        if edge["to"] in parent:
            raise ValueError("tree nodes must have only one parent; use dependency for fan-in")
        parent[edge["to"]] = edge["from"]
    if len(parent) != len(nodes) - 1:
        raise ValueError(
            "tree needs one root and a connected parent-child edge for every other node"
        )
    for node in nodes:
        seen = set()
        current = node["id"]
        while current in parent:
            if current in seen:
                raise ValueError("parent cycle is not a tree")
            seen.add(current)
            current = parent[current]
    return parent


def validate(spec, kind):
    if not isinstance(spec, dict) or spec.get("type") != kind:
        raise ValueError(f"expected type {kind}")
    fields(
        spec,
        {"type", "title", "actors", "nodes", "edges", "motion"} | EXTRA_TOP.get(kind, set()),
        kind,
    )
    label(spec.get("title"), 96)
    if spec.get("motion", "none") not in {"none", "reveal", "loop"}:
        raise ValueError("motion must be none, reveal or loop")
    actors = names(spec.get("actors", ["Reader"]), "actors", maximum=6)
    nodes = spec.get("nodes")
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= LIMITS[kind]:
        raise ValueError(f"{kind}: split the diagram; expected 1..{LIMITS[kind]} nodes")
    ids = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("nodes must be objects")
        fields(node, COMMON_NODE | EXTRA_NODE[kind], f"{kind} node")
        if not isinstance(node.get("id"), str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]{0,23}", node["id"]
        ):
            raise ValueError("node id must be short letters, digits or underscores")
        if node["id"] in ids:
            raise ValueError("duplicate node id")
        ids.add(node["id"])
        label(node.get("label"), 32)
        refs(node)
        if node.get("actor", actors[0]) not in actors:
            raise ValueError("node actor is not declared")
    if len(nodes) < 5 and len(actors) == 1:
        raise ParagraphRequired("write a paragraph: fewer than 5 items with one actor")
    edges = spec.get("edges", [])
    if not isinstance(edges, list) or len(edges) > 14:
        raise ValueError("split the diagram: at most fourteen connections")
    if kind in NO_EDGES and edges:
        raise ValueError(f"{kind} has no connectors")
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("edges must be objects")
        fields(
            edge,
            {"from", "to", "label"}
            | (
                {"weight"}
                if kind == "sankey"
                else {"snapshot"}
                if kind == "architecture-delta"
                else {"kind"}
                if kind == "uml-class"
                else {"from_card", "to_card"}
                if kind == "db-schema"
                else set()
            ),
            "edge",
        )
        if edge.get("from") not in ids or edge.get("to") not in ids:
            raise ValueError("edge endpoint is missing")
        label(edge.get("label"), 48)
        if kind == "architecture-delta" and edge.get("snapshot", "both") not in {
            "before",
            "after",
            "both",
        }:
            raise ValueError("delta edge snapshot must be before, after or both")
        if kind == "uml-class" and edge.get("kind") not in RELATIONS:
            raise ValueError("class relationships need a documented kind")
        if kind == "db-schema" and any(
            edge.get(k) not in {"1", "N", "0..1", "1..*"} for k in ("from_card", "to_card")
        ):
            raise ValueError("schema relationships need explicit cardinalities")
    if kind in {"tree", "org-chart"}:
        tree_parents(spec)
    if kind == "nested":
        pseudo = dict(
            spec, edges=[{"from": n["parent"], "to": n["id"]} for n in nodes if n.get("parent")]
        )
        if any(e["from"] not in ids for e in pseudo["edges"]):
            raise ValueError("unknown containment parent")
        tree_parents(pseudo)
    if (
        kind in VARIANTS
        and spec.get("variant", next(iter(sorted(VARIANTS[kind])))) not in VARIANTS[kind]
    ):
        raise ValueError(f"unknown {kind} variant")
    if kind in {"bar", "line", "polar", "pyramid", "treemap", "waterfall", "heatmap", "sankey"}:
        label(spec.get("unit"), 24)
    if kind in {"quadrant", "scatter"}:
        label(spec.get("x_axis"), 24)
        label(spec.get("y_axis"), 24)
    if kind == "radar":
        names(spec.get("axes"), "axes", 3, 6)
        number(spec.get("maximum"), "maximum", 0.001, 1e9)
    if kind == "polar":
        number(spec.get("maximum"), "maximum", 0.001, 1e9)
    if kind == "line":
        names(spec.get("categories"), "categories", 2, 9)
        if spec.get("variant") == "slopegraph" and len(spec["categories"]) != 2:
            raise ValueError("slopegraph needs exactly two endpoint categories")
    if kind in {"dp-security-matrix", "heatmap", "kanban"}:
        names(spec.get("columns"), "columns", 1, 5)
    if kind == "heatmap":
        names(spec.get("rows"), "rows", 1, 5)
    if kind == "architecture":
        names(spec.get("zones"), "zones", 1, 5)
    if kind == "architecture-delta":
        strings(spec.get("changes"), "changes", 6)
        if not spec["changes"]:
            raise ValueError("architecture delta needs an explicit change ledger")
    if kind == "fishbone":
        label(spec.get("effect"), 48)
    for node in nodes:
        if kind in {"timeline", "gantt"}:
            start = iso(node.get("date" if kind == "timeline" else "start"), "date")
            if kind == "gantt" and iso(node.get("end"), "end") < start:
                raise ValueError("end must not precede start")
        for key in EXTRA_NODE[kind] - {
            "values",
            "value",
            "compare",
            "x",
            "y",
            "size",
            "samples",
            "evolution",
            "visibility",
            "parent",
            "segments",
            "total",
            "stage",
            "replicas",
            "attributes",
            "operations",
            "columns",
            "permissions",
            "members",
            "date",
            "start",
            "end",
        }:
            if key in node:
                label(node[key], 32)
        if kind in {
            "architecture",
            "architecture-delta",
            "it-current-state",
            "process",
            "data-flow",
            "dp-integration",
            "deployment",
            "org-chart",
            "layer-stack",
            "fishbone",
            "kanban",
        }:
            required = {
                "architecture": ("zone", "kind"),
                "architecture-delta": ("status",),
                "it-current-state": ("department", "condition"),
                "process": ("input", "output"),
                "data-flow": ("lane", "payload"),
                "dp-integration": ("zone", "protocol"),
                "deployment": ("host", "zone"),
                "org-chart": ("role",),
                "layer-stack": ("responsibility",),
                "fishbone": ("category",),
                "kanban": ("column", "state", "owner"),
            }[kind]
            for key in required:
                label(node.get(key), 32)
        if kind == "architecture" and node["zone"] not in spec["zones"]:
            raise ValueError("node zone is not declared")
        if kind == "architecture-delta" and node["status"] not in {
            "unchanged",
            "added",
            "removed",
            "changed",
        }:
            raise ValueError("delta status must be unchanged, added, removed or changed")
        if kind == "architecture-delta" and node["status"] == "changed":
            label(node.get("before_label"), 32)
            label(node.get("after_label"), 32)
        if kind in {"quadrant", "scatter"}:
            number(node.get("x"), "x", 0, 1)
            number(node.get("y"), "y", 0, 1)
            if kind == "scatter" and spec.get("variant") == "bubble":
                number(node.get("size"), "bubble size", 1, 400)
            if kind == "scatter" and spec.get("variant") == "box-plot":
                vals = node.get("samples")
                if not isinstance(vals, list) or len(vals) != 5:
                    raise ValueError("box-plot needs sorted min, q1, median, q3, max samples")
                for v in vals:
                    number(v, "sample", 0, 1)
                if vals != sorted(vals):
                    raise ValueError("box-plot samples must be ordered")
        if kind == "wardley":
            number(node.get("evolution"), "evolution", 0, 1)
            number(node.get("visibility"), "visibility", 0, 1)
        if kind in {"radar", "line"}:
            vals = node.get("values")
            expected = len(spec["axes" if kind == "radar" else "categories"])
            if not isinstance(vals, list) or len(vals) != expected:
                raise ValueError("one value is required for every axis/category")
            for v in vals:
                number(v, "series value", 0, spec["maximum"] if kind == "radar" else 1e9)
        if kind in {"polar", "pyramid", "treemap", "heatmap", "bar", "waterfall"}:
            number(
                node.get("value"),
                "value",
                -1e9 if kind == "waterfall" else 0,
                spec["maximum"] if kind == "polar" else 1e9,
            )
            if kind in {"pyramid", "treemap"} and node["value"] <= 0:
                raise ValueError("area/width values must be positive")
            if kind == "bar" and spec.get("variant") == "dumbbell":
                number(node.get("compare"), "compare", 0, 1e9)
            if kind == "waterfall" and "total" in node and not isinstance(node["total"], bool):
                raise ValueError("total must be boolean")
        if kind == "treemap" and spec.get("variant") == "marimekko":
            vals = node.get("segments")
            if not isinstance(vals, list) or not 1 <= len(vals) <= 5:
                raise ValueError("marimekko needs 1..5 segment amounts")
            for v in vals:
                number(v, "segment", 0, 1e9)
            if sum(vals) <= 0:
                raise ValueError("segment total must be positive")
        if kind == "venn":
            names(node.get("members"), "members", 1, 9)
        if kind == "heatmap" and (
            node.get("row") not in spec["rows"] or node.get("column") not in spec["columns"]
        ):
            raise ValueError("heatmap cell needs a declared row and column")
        if kind == "dp-security-matrix":
            vals = node.get("permissions")
            if (
                not isinstance(vals, list)
                or len(vals) != len(spec["columns"])
                or any(v not in {"allow", "deny", "unknown"} for v in vals)
            ):
                raise ValueError("matrix needs allow/deny/unknown per column")
        if kind == "kanban" and (
            node["column"] not in spec["columns"]
            or node["state"] not in {"queued", "doing", "blocked", "waiting", "done"}
        ):
            raise ValueError("card needs a declared column and known state")
        if kind in {"uml-class", "db-schema"}:
            for key in ("attributes", "operations") if kind == "uml-class" else ("columns",):
                strings(node.get(key), key, 5)
        if kind == "sankey":
            number(node.get("stage"), "stage", 0, 3)
            if not isinstance(node["stage"], int):
                raise ValueError("stage must be integer")
        if kind == "deployment":
            number(node.get("replicas"), "replicas", 1, 99)
    if kind == "heatmap" and len({(n["row"], n["column"]) for n in nodes}) != len(nodes):
        raise ValueError("duplicate heatmap cell")
    if kind == "kanban":
        limits = spec.get("limits", {})
        if not isinstance(limits, dict) or set(limits) - set(spec["columns"]):
            raise ValueError("limits must name declared columns")
        for v in limits.values():
            number(v, "WIP limit", 1, 12)
    if kind == "sankey" and not edges:
        raise ValueError("sankey needs explicit weighted edges")
    if kind == "sankey":
        by_id = {n["id"]: n for n in nodes}
        for e in edges:
            number(e.get("weight"), "weight", 0.001, 1e9)
            if by_id[e["from"]]["stage"] >= by_id[e["to"]]["stage"]:
                raise ValueError("sankey edges must advance a stage")
        for n in nodes:
            incoming = sum(e["weight"] for e in edges if e["to"] == n["id"])
            outgoing = sum(e["weight"] for e in edges if e["from"] == n["id"])
            if incoming and outgoing and abs(incoming - outgoing) > 1e-6:
                raise ValueError("sankey intermediate flow must balance")
    if kind == "loop":
        if len(edges) != len(nodes) or any(
            sum(e["from"] == n["id"] for e in edges) != 1
            or sum(e["to"] == n["id"] for e in edges) != 1
            for n in nodes
        ):
            raise ValueError("loop needs one incoming and outgoing edge per node")
        seen = set()
        cursor = nodes[0]["id"]
        outgoing = {e["from"]: e["to"] for e in edges}
        while cursor not in seen:
            seen.add(cursor)
            cursor = outgoing[cursor]
        if len(seen) != len(nodes):
            raise ValueError("loop must be one connected cycle")
    return spec
