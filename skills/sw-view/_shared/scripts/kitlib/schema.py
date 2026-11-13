"""Constants shared by more than one skill: statuses, story sections, RTM and registry columns."""

from __future__ import annotations

SKILL_PREFIX = "sw-"
KIT_NAME = "specwright"
# Mirrors pyproject.toml (tools/validate.py checks it) so a running skill can name its version.
KIT_VERSION = "0.6.0"

STORY_SECTIONS = [
    "Goal",
    "Context",
    "Acceptance criteria",
    "Business rules",
    "Edge cases and error behavior",
    "Non-functional",
    "UI/UX",
    "Out of scope",
    "Dependencies and relations",
    "Open questions",
    "DoR checklist",
    "Identity",
]

_CARD_STATUSES = ["draft", "in-review", "approved", "superseded", "withdrawn"]

STATUSES = {
    "feature": [
        "draft",
        "in-review",
        "ready-to-publish",
        "published",
        "ready-for-dev",
        "superseded",
        "withdrawn",
    ],
    "snapshot": ["raw"],
    "asset": ["captured", "superseded", "withdrawn"],
    "src": ["raw"],
    "q": ["proposed", "candidate", "open", "assumed", "answered", "withdrawn"],
    "cr": ["proposed", "in-review", "approved", "applied", "withdrawn"],
    "amendment": ["proposed", "applied", "rejected", "withdrawn"],
    "candidates": ["raw", "verified", "withdrawn"],
    "dec": ["accepted", "superseded"],
    "idea": ["draft", "accepted", "withdrawn"],
    "epic": ["draft", "approved", "superseded", "withdrawn"],
    "task": ["draft", "ready", "withdrawn"],
    "bo": _CARD_STATUSES,
    "br": _CARD_STATUSES,
    "fr": _CARD_STATUSES,
    "nfr": _CARD_STATUSES,
    "stk": _CARD_STATUSES,
    "risk": [*_CARD_STATUSES, "open", "mitigated"],
}

# Evidence kinds a decision may cite. Chat is opt-in per project because it is the weakest.
DEFAULT_EVIDENCE_KINDS = ("url", "ticket", "document", "meeting")
# `session` is the owner deciding in this session; it needs no URL and is allowed only when
# sign-off is optional.
SESSION_EVIDENCE = "session"
EVIDENCE_KINDS = (*DEFAULT_EVIDENCE_KINDS, "chat", SESSION_EVIDENCE)

# Question states that still wait for an answer; every board and report counts the same set.
# An `assumed` question is not waiting: its default was applied, and it can still be answered.
OPEN_Q = frozenset({"proposed", "candidate", "open"})
ANSWERABLE_Q = OPEN_Q | {"assumed"}

DEFAULT_STATUS_MAP = {
    "published": "To Do",
    "ready-for-dev": "Ready for Dev",
    "in-development": "In Progress",
    "superseded": "Won't Do",
    "withdrawn": "Won't Do",
}

# RTM columns as (name, owning skill). The trace skill owns rows; every other skill
# writes only the one column assigned to it.
RTM_ID_COLUMN = "Spec ID"
RTM_COLUMNS = [
    ("BO", "sw-spec"),
    ("BR/NFR", "sw-spec"),
    ("Story draft", "sw-spec"),
    ("Jira", "sw-publish"),
    ("Jira status", "sw-publish"),
    ("Sign-off", "sw-review"),
    ("Drift", "sw-publish"),
    ("Test ref", "qa"),
]

# Delivery layers a task may carry as a title prefix: `### TASK-001-1 — [backend] Title`.
# One layer per task; work that spans layers is split into one task per layer.
TASK_LAYERS = ("backend", "frontend", "mobile", "devops", "data", "qa", "design", "docs")
# Layers that build what a user sees; they cite the visual reference they implement.
UI_TASK_LAYERS = ("frontend", "mobile", "design")
# Asset kinds (asset-kind.md) that show a design: a story or task links them, never fetches them.
VISUAL_ASSET_KINDS = ("figma", "mockup", "image", "diagram")

ASSET_REGISTRY_COLUMNS = [
    "Asset ID",
    "File",
    "Kind",
    "sha256",
    "Captured",
    "Source",
    "Refs",
    "State",
]

REGISTRY_COLUMNS = [
    "Spec ID",
    "Kind",
    "Jira key",
    "Confluence id",
    "Label",
    "Entity property",
    "Last published draft hash",
    "Last snapshot",
    "State",
    "Title",
    "Aliases",
    "Source ref",
]

SCOPE_DIRS = [
    "00-inbox/raw",
    "00-inbox/imports",
    "01-analysis/ideas",
    "01-analysis/epics",
    "01-analysis/candidates",
    "01-analysis/baseline",
    "02-drafts",
    "03-plan",
    "assets",
    "diagrams",
    "records",
    "snapshots/jira",
    "snapshots/confluence",
    "_meta",
    "_meta/work",
]

OUTPUT_CHOICES = ("ask", "markdown", "jira", "both")
DEFAULT_OUTPUT = "markdown"

# Governance: how much ceremony a workspace wants. `optional` sign-off lets the owner accept a
# story in plain words; `required` keeps the formal sign-off from a configured approver.
# `guided` flow runs station to station with one plain confirmation; `step` stops at each one.
SIGNOFF_MODES = ("optional", "required")
FLOW_MODES = ("guided", "step")
DEFAULT_GOVERNANCE = {"signoff": "optional", "flow": "guided"}
GOVERNANCE_CHOICES = {"signoff": SIGNOFF_MODES, "flow": FLOW_MODES}

# The stored status keeps its name so no data migrates; readers see the plain word.
STATE_LABELS = {"ready-to-publish": "accepted"}
GRAPH_DIR = "_meta/graph"
# Derived, git-ignored views of the spec for the console and any other reader (dataformat.py).
DATA_DIR = "_meta/data"
GRAPH_SCHEMA_VERSION = 3

# The closed set of graph relations; a link outside this set is never recorded.
RELATIONS = (
    "member_of",
    "realizes",
    "governed_by",
    "sourced_from",
    "shaped_from",
    "source_parent",
    "has_ac",
    "has_task",
    "implements",
    "touches",
    "affects",
    "supersedes",
    "illustrates",
    "exercises",
    "derives_from",
    "published_as",
    "last_snapshot",
    "external_parent",
    "blocks",
    "mentions",
)
