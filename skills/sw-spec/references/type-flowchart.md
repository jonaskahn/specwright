# flowchart

## Best for

Decision branches and alternative process paths.

## Not this type

Use state for object status; swimlane for ownership.

## Layout conventions

Flow is top to bottom. Start/end terminals are rounded, steps rectangular, decisions diamond-shaped and merges dots.
Label every branch; decisions allow three exits.

## Focal rule

Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget

Nine nodes; split rather than add crossings.

## JSON additions

Set node kind to start, end, step, decision or merge. Edges need explicit branch conditions. Colour never encodes shape
type.
Common contract and CLI codes: references/style.md. Examples are illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
