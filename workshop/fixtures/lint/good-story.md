---
id: FEAT-001
type: feature
scope: REF
title: Submit a return request
aliases: []
status: ready-to-publish
bo: [BO-001]
signoffs:
  - PO | Mira Chen | 2026-11-10 | https://approval.example/returns/1 | sha256:635df67d3285689a4350d1891ce59836ceefb6ddb4f9d2db9e534ad46a7e530c
---
## Goal
As a buyer with a delivered parcel, I want to request a return so that I can recover its price. Business objective: BO-001.
## Context
Returns currently require a phone call.
## Acceptance criteria
### AC-001-1 — Return during the window
Given a parcel delivered 6 days ago
When the buyer requests a return
Then the request has status "Awaiting inspection" and the original price is recorded
### AC-001-2 — Return outside the window
Given a parcel delivered 22 days ago
When the buyer requests a return
Then no request is created and "Return period ended" is displayed
## Business rules
- Requests are accepted for 21 calendar days. Example: delivery on 2026-10-01 permits a request on 2026-10-21.
## Edge cases and error behavior
- IF a parcel has no delivery date THEN display "Contact support".
## Non-functional
- Response time p95 is below 900 ms under 80 concurrent buyers, measured over 10 minutes.
## UI/UX
States: default, empty, loading, error.
## Out of scope
- Automatic reimbursement — reason: inspection determines the amount.
## Dependencies and relations
None — no dependency recorded.
## Open questions
None — no open question.
## DoR checklist
- [x] Observable examples and return window are recorded.
## Identity
Spec ID: REF:FEAT-001 · Project: REF · Managed by specwright
