# service-blueprint

## Best for

Visible delivery linked to internal support.

## Not this type

Use journey for feelings; swimlane for sequential ownership.

## Layout conventions

Stages cross evidence, customer, frontstage, backstage and support rows. A heavy visibility line separates frontstage
and backstage. Internal rows are tinted; no arrows.

## Focal rule

Use shape and visible source IDs before accent. Keep at most one spec-linked
cell accented; never invent a source reference for emphasis.

## Complexity budget

Nine stages, five layers; one focal cell at most during manual editing.

## JSON additions

Node cells map layer names to text. Omitted cells display n/a; ask before treating unknown as not applicable. HTML or
standalone SVG.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.

## Output

Use assets/service-blueprint.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.
