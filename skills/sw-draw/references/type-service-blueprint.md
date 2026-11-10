# service-blueprint

## Best for

Visible delivery linked to internal support.

## Not this type

Use journey for feelings; swimlane for sequential ownership.

## Layout conventions

Stages cross evidence, customer, frontstage, backstage and support rows. A heavy visibility line separates frontstage
and backstage. Internal rows are tinted; no arrows.

## Focal rule

Use shape and visible source IDs before accent. Keep at most one spec-linked
cell accented; never invent a source reference for emphasis.

## Complexity budget

Nine stages, five layers; one focal cell at most during manual editing.

## JSON additions

Node cells map layer names to text. Omitted cells display n/a; ask before treating unknown as not applicable. HTML or
standalone SVG.
The common contract and CLI codes are in style.md. The matching JSON in
fixtures/refund/diagrams is illustrative, not approved policy.

## Anti-patterns

Do not compress labels until they lose meaning, hide unsupported branches, or
present missing knowledge as confirmed. Split unreadable pictures and ask for
absent evidence. Confirm each spec-linked box against the draft.
