# journey

## Best for

One persona moving through actions and touchpoints.

## Not this type

Use flowchart when feelings lack evidence; blueprint for internal delivery.

## Layout conventions

Stage columns cross actions, touchpoints and owner rows, followed by a mandatory feeling curve. Levels are high,
neutral, low, never numeric ratings.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Six stages, three content rows, two pain markers at low points.

## JSON additions

Each node needs feeling, touchpoint and owner. Optional pain is true only at low feeling. One actors entry names the
persona. Mermaid syntax requires ordinal scores; HTML displays named feelings.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.

## Output

Use assets/journey.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
A Mermaid companion (`.mmd` beside the output) is emitted; it is editable, not a pixel-identical export.
