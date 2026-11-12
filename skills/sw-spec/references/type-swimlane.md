# swimlane

## Best for

Ownership and handoffs between named actors.

## Not this type

Use flowchart when ownership is irrelevant; sequence for message timing.

## Layout conventions

Vertical lanes name actors and the flow reads top to bottom. Each step belongs to exactly one lane; crossing lanes means a handoff. Narrative order
reads left to right.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Nine steps, six actors; split by responsibility boundary.

## JSON additions

Add actor to every node using a declared actors name. Edges describe handoffs.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.

## Output

Use assets/swimlane.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.
