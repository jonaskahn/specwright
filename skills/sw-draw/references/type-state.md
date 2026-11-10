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
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
