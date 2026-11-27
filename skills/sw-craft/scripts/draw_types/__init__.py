"""Closed type roster; names are never imported from untrusted input.

The roster names every supported type. A build ships only some of them: CORE types ship in
every build, EXTENDED types only in a full install, and the rest live under ``extras/``.
``available()`` reports what this build actually carries.
"""

from pathlib import Path

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

# Core types ship in every build: a core-only package carries exactly these and nothing else.
CORE = (
    "swimlane",
    "flowchart",
    "state",
    "sequence",
    "journey",
    "story-map",
    "er",
    "process",
    "data-flow",
    "architecture-delta",
)
# Every other type ships in the skill folder and is copied into extras/ of a core package. A core
# package is made by moving these out, so the validator finds each one in exactly one place.
EXTENDED = tuple(t for t in TYPES if t not in CORE)
_REFERENCES = Path(__file__).resolve().parent.parent.parent / "references"


def available():
    """Roster types whose reference ships in this build, in roster order."""
    return tuple(t for t in TYPES if (_REFERENCES / f"type-{t}.md").is_file())
