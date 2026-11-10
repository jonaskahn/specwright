"""Constants shared by more than one skill: statuses, story sections, RTM and registry columns."""

from __future__ import annotations

SKILL_PREFIX = "sw-"
KIT_NAME = "specwright"

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
    "src": ["raw"],
    "q": ["candidate", "open", "answered", "withdrawn"],
    "cr": ["proposed", "in-review", "approved", "applied", "withdrawn"],
    "dec": ["accepted", "superseded"],
    "idea": ["draft", "accepted", "withdrawn"],
    "bo": _CARD_STATUSES,
    "br": _CARD_STATUSES,
    "fr": _CARD_STATUSES,
    "nfr": _CARD_STATUSES,
    "stk": _CARD_STATUSES,
    "risk": [*_CARD_STATUSES, "open", "mitigated"],
}

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
    ("Jira status", "sw-sync"),
    ("Sign-off", "sw-review"),
    ("Drift", "sw-sync"),
    ("Test ref", "qa"),
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
]

SCOPE_DIRS = [
    "00-inbox/raw",
    "01-analysis/ideas",
    "02-drafts",
    "diagrams",
    "records",
    "snapshots/jira",
    "snapshots/confluence",
    "_meta",
]
