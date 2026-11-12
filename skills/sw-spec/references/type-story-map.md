# story-map

## Best for

Activity backbone, walking skeleton and releases by outcome.

## Not this type

Use state for statuses; story maps are not kanban.

## Layout conventions

Activities read left to right. Cards beneath form a walking skeleton. Outcome slices form rows with heavy release cuts.
No dates or sentiment.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Five activities, three slices, twelve cards.

## JSON additions

Declare activities and slices arrays. Every node needs activity and slice matching those names. Cards sharing a cell
stack. Edges are forbidden. HTML or standalone SVG.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.

## Output

Use assets/story-map.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.
