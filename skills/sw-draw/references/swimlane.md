# swimlane

## Best for
Ownership and handoffs between named actors.

## Not this type
Use flowchart when ownership is irrelevant; sequence for message timing.

## Layout conventions
Horizontal lanes name actors. Each step belongs to exactly one lane; crossing lanes means a handoff. Narrative order reads left to right.

## Focal rule
Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget
Nine steps, six actors; split by responsibility boundary.

## JSON additions
Add actor to every node using a declared actors name. Edges describe handoffs.
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns
Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
