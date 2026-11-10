"""Closed type roster; names are never imported from untrusted input."""

LEGACY = (
    "swimlane",
    "flowchart",
    "journey",
    "service-blueprint",
    "story-map",
    "state",
    "sequence",
    "er",
)
TEMPLATES = ("exploded-axonometric", "axonometric-plan", "medallion", "high-level")
GRAPHS = (
    "architecture",
    "architecture-delta",
    "it-current-state",
    "process",
    "data-flow",
    "dp-integration",
    "deployment",
    "dependency",
)
HIERARCHIES = ("tree", "org-chart", "nested", "layer-stack", "loop", "fishbone")
CHARTS = (
    "quadrant",
    "radar",
    "polar",
    "pyramid",
    "treemap",
    "heatmap",
    "bar",
    "waterfall",
    "line",
    "scatter",
    "wardley",
)
OTHER = (
    "timeline",
    "gantt",
    "venn",
    "dp-security-matrix",
    "sankey",
    "kanban",
    "uml-class",
    "db-schema",
)
TYPES = LEGACY + GRAPHS + HIERARCHIES + CHARTS + OTHER + TEMPLATES
MERMAID = frozenset(
    ("flowchart", "sequence", "state", "er", "journey", "timeline", "gantt", "quadrant", "tree")
)
STRUCTURED = tuple(t for t in TYPES if t not in TEMPLATES)
