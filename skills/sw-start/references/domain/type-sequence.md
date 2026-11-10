# sequence

## Best for

Order of participant exchanges.

## Not this type

Use swimlane for responsibility; state for lifecycle.

## Layout conventions

Participants sit above dashed lifelines. Calls are solid with filled heads, returns dashed with filled heads, async
dashed with open heads. Receiving work has activation bars.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Nine participants, twice as many messages, two frames.

## JSON additions

Nodes are participants. Edge kind is call, return or async. Optional frames have kind alt, opt or loop, label, start and
end inclusive zero-based message indexes. Frames must not cross. Use separate drawings for nested alternatives; no
free-floating if/else arrows.
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
