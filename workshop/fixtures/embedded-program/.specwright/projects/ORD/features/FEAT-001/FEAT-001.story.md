---
id: FEAT-001
type: feature
scope: ORD
status: draft
bo: [BO-001]
epic: [REF:EPIC-001]
---
# Refund entry

## Goal
As a customer, I want to lodge a refund. Supports BO-001.

## Context
Cross-project epic.

## Acceptance criteria
### AC-001-1 — Lodge
Given a delivered order,
When the owner asks for a refund,
Then a request is created.

### AC-001-2 — Window
Given an order past the window,
When the owner asks for a refund,
Then no request is created.

## Business rules
- BR-001 window is 14 days. Example: 6 days -> eligible.

## Edge cases and error behavior
None — none defined.

## Non-functional
- NFR-DOM-001: response p95 below 900 ms. Example: measured over 10 minutes.

## UI/UX
States: default, empty, loading, error.

## Out of scope
No payout — reason: finance owns it.

## Dependencies and relations
None — no dependency.

## Open questions
None

## DoR checklist
- [x] Goal links a BO.
- [x] At least two concrete G/W/T criteria.
- [x] BR examples and measurable NFRs.
- [x] UI states and exclusions with reasons.
- [x] No unresolved questions or markers.
- [x] Dev and QA checks pass for each AC.
- [x] PO approval evidence recorded.

## Identity
Spec ID: ORD:FEAT-001 · Project: ORD · Draft hash: sha256:0000000000000000000000000000000000000000000000000000000000000000 · Managed by specwright
Dev consumer check: pass.
QA consumer check: pass.
