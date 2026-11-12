# state

## Best for

Legal lifecycle transitions of one object.

## Not this type

Use flowchart for work steps; sequence for participant messages.

## Layout conventions

Rounded states, filled start dot, ringed terminal dot. Transitions read event [guard] / action. Self-loops route above
the state.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Nine states; at most twice as many transitions.

## JSON additions

Edges are transitions; first node is initial, last is terminal. Avoid duplicated error arrows: record one shared * to
Error condition in source context instead. Ask before assuming guards or terminal status.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.

## Output

Use assets/state.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
A Mermaid companion (`.mmd` beside the output) is emitted; it is editable, not a pixel-identical export.
