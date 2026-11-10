---
id: FEAT-001
type: feature
scope: APP
status: ready-to-publish
bo: [BO-001]
---
# Submit a refund request

## Goal
As a customer, I want to submit a refund so that I get my money back. Supports BO-001.

## Context
A customer paid for an order.

## Acceptance criteria
### AC-001-1 — Eligible request
Given order R100 paid 50 USD on 2026-11-01,
When its owner requests a refund,
Then one pending request for 50 USD is recorded.

### AC-001-2 — Expired request
Given an order older than the agreed window,
When its owner requests a refund,
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
Spec ID: APP:FEAT-001 · Project: APP · Draft hash: sha256:0000000000000000000000000000000000000000000000000000000000000000 · Managed by specwright
Dev consumer check: pass.
QA consumer check: pass.
