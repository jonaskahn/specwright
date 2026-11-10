# er

## Best for
Conceptual entities and relationship multiplicity.

## Not this type
Use sw-spec for physical storage requirements; state for lifecycles.

## Layout conventions
Entity boxes have headers and fields. PK marks a key, FK a reference. Cardinalities appear at both ends. Accent can identify a spec-linked aggregate root.

## Focal rule
Use shape and visible source IDs before accent. Keep at most two spec-linked
nodes accented; never invent a source reference for emphasis.

## Complexity budget
Nine entities, four fields each; split by aggregate.

## JSON additions
Nodes add fields as identifiers optionally prefixed PK or FK. Edges need from_card and to_card, each 1, N, 0..1 or 1..*. Never infer physical settings.
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns
Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
