# story-map

## Best for
Activity backbone, walking skeleton and releases by outcome.

## Not this type
Use state for statuses; story maps are not kanban.

## Layout conventions
Activities read left to right. Cards beneath form a walking skeleton. Outcome slices form rows with heavy release cuts. No dates or sentiment.

## Focal rule
Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget
Five activities, three slices, twelve cards.

## JSON additions
Declare activities and slices arrays. Every node needs activity and slice matching those names. Cards sharing a cell stack. Edges are forbidden. HTML only.
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns
Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
