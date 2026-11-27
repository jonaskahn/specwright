"""Dispatch each structured type to its geometry builder; data never supplies SVG."""

from __future__ import annotations

import importlib

from draw_graphs import FLOW_KINDS, class_graph, delta, flow_graph, tree_graph
from draw_types import LEGACY

PLOTS = (
    "bar",
    "waterfall",
    "line",
    "scatter",
    "quadrant",
    "wardley",
    "radar",
    "polar",
    "pyramid",
    "treemap",
    "heatmap",
    "sankey",
)
BOARDS = (
    "nested",
    "layer-stack",
    "loop",
    "fishbone",
    "kanban",
    "venn",
    "timeline",
    "gantt",
    "dp-security-matrix",
)


def build(spec):
    """Return the Canvas for a validated structured spec."""
    kind = spec["type"]
    if kind in LEGACY:
        return importlib.import_module("draw_legacy").build(spec)
    if kind == "architecture-delta":
        return delta(spec)
    if kind in FLOW_KINDS:
        return flow_graph(spec)
    if kind in {"tree", "org-chart"}:
        return tree_graph(spec)
    if kind in {"uml-class", "db-schema"}:
        return class_graph(spec)
    if kind in PLOTS:
        return importlib.import_module("draw_plots").build(spec)
    if kind in BOARDS:
        return importlib.import_module("draw_boards").build(spec)
    raise ValueError("unknown structured type")


def render_geometry(spec):
    return build(spec).finish()[:3]


def layout(spec):
    """Node card boxes recorded while drawing; marks without cards are not boxed."""
    return dict(build(spec).boxes)
