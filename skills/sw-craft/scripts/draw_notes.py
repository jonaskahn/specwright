"""Display names and one-sentence readings for each drawing type."""

NAMES = {
    "er": "ER / data model",
    "dp-integration": "DP integration",
    "dp-security-matrix": "DP security matrix",
    "it-current-state": "IT current state",
    "db-schema": "Database schema",
    "uml-class": "UML class",
}

DESCRIPTIONS = {
    "architecture": (
        "Cards are components grouped into zone columns; each connector names its relation."
    ),
    "architecture-delta": (
        "Before and after share one layout. Each card states added, removed, changed or "
        "unchanged, and the change list names every edit."
    ),
    "bar": (
        "Bars start at zero on one shared scale and carry their exact values. Dumbbells "
        "compare two supplied values per row."
    ),
    "data-flow": (
        "Each step sits in its lane and names its payload. Connectors explain movement, "
        "not approval."
    ),
    "db-schema": (
        "Tables list their declared columns. Crow's-foot ends show both cardinalities; no "
        "SQL is executed."
    ),
    "dependency": (
        "Directed connections keep shared dependencies and cycles; a dashed return closes a cycle."
    ),
    "deployment": "Placement cards name hosts, trust zones and replica counts.",
    "dp-integration": "Zones group integration endpoints; each card names its protocol.",
    "dp-security-matrix": (
        "Each cell shows allow, deny or unknown as a glyph and a word; unknown is never "
        "read as deny."
    ),
    "er": (
        "Entities list their fields; PK marks a key and FK a reference. Crow's-foot ends "
        "show cardinality."
    ),
    "fishbone": (
        "Category branches meet the effect on the spine; causes stay hypotheses until verified."
    ),
    "flowchart": (
        "Rounded terminals start or end a path, rectangles are steps and diamonds are "
        "decisions. Each branch carries its condition."
    ),
    "gantt": (
        "Bars share one calendar scale with month ticks; an end date never precedes its start."
    ),
    "heatmap": (
        "Cell shade follows an ordered ramp and every cell prints its value, so colour is "
        "never the only signal."
    ),
    "it-current-state": (
        "Systems are grouped by department, each with its observed condition; no "
        "modernization plan is implied."
    ),
    "journey": (
        "Columns follow one persona. The curve plots named high, neutral and low "
        "feelings; Pain marks a trough, not a measurement."
    ),
    "kanban": (
        "Cards sit in explicit columns with text states and count/limit headers; an over- "
        "limit column says so."
    ),
    "layer-stack": "Layers are stacked in supplied order, each with its named responsibility.",
    "line": (
        "Categories keep source order on one shared scale; each series is labelled at its end."
    ),
    "loop": "One connected cycle feeds back to its first stage; numerals give the order.",
    "nested": "Enclosing boundaries carry scope; children sit visibly inside their parent.",
    "org-chart": "Reporting lines form a rooted tree; role text implies no approval.",
    "polar": "Angle is category and radial distance is magnitude on one shared maximum.",
    "process": "Stages name their input and output; connectors say what each hand-off supplies.",
    "pyramid": (
        "Tiers are ordinal. In funnel mode bar width is proportional to value; widths are "
        "not probabilities."
    ),
    "quadrant": "Positions lie on two named 0 to 1 axes; the crossing lines mark the midpoints.",
    "radar": "All spokes share a stated maximum; scores are exact in the data table.",
    "sankey": (
        "Band width follows one scale; flow into each intermediate stage equals flow out of it."
    ),
    "scatter": (
        "Positions use two named 0 to 1 axes. Bubble area maps size; box plots show five "
        "ordered statistics."
    ),
    "sequence": (
        "Participants run left to right and time runs down. Solid arrows call, dashed "
        "arrows return, open heads are asynchronous; frames bound alternatives and loops."
    ),
    "service-blueprint": (
        "Columns are stages. The heavy line separates frontstage from backstage; empty "
        "cells say n/a."
    ),
    "state": (
        "Rounded boxes are states; the filled dot starts the path and the ringed dot ends "
        "it. Transitions name event, guard and action."
    ),
    "story-map": (
        "Columns form the activity backbone; heavy lines cut outcome-based release slices."
    ),
    "swimlane": "Each lane belongs to one actor; an arrow that crosses lanes is a handoff.",
    "timeline": "Event positions are proportional to elapsed days.",
    "tree": "Depth encodes parentage; every node has one parent except the root.",
    "treemap": (
        "Area is proportional to value. Marimekko width is value and height is within- "
        "column share."
    ),
    "uml-class": (
        "Compartments separate attributes from operations; end markers show the relationship kind."
    ),
    "venn": (
        "Circles denote membership, not proportional area; the list names every intersection."
    ),
    "wardley": (
        "Horizontal evolution and vertical visibility are supplied judgments, not "
        "measured maturity."
    ),
    "waterfall": (
        "Steps start at the previous subtotal; marked totals start at zero. Blue rises, "
        "orange falls, grey is a total."
    ),
}


def name(kind):
    return NAMES.get(kind, kind.replace("-", " ").capitalize())
