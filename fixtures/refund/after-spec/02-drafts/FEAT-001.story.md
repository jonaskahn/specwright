---
id: FEAT-001
type: feature
scope: REF
title: Submit a refund request
aliases: []
status: in-review
bo: [BO-001]
updated: 2026-11-10
---
# Submit a refund request

## Goal
Let customers request a refund online; supports BO-001.

## Context
A customer has paid for an order and needs to return it.

## Acceptance criteria
### AC-001-1 — Eligible request
Given order R100 was paid 50 USD on 2026-11-01,
when the buyer requests a refund on 2026-11-05,
then the request is recorded as "Awaiting decision" for 50 USD.

### AC-001-2 — Duplicate request
Given order R100 already has an awaiting request,
when the buyer submits it again,
then no second request is created and "Request already exists" is shown.

## Business rules
Eligibility is limited to 14 days after payment.

## Edge cases and error behavior
A missing order shows "Order not found" and creates no request.

## Non-functional
None.

## UI/UX
Show the recorded amount and current request state.

## Out of scope
Automatic payment reversal is excluded; approval is handled separately.

## Dependencies and relations
BO-001.

## Open questions
Q-001 asks whether shipping charges count in the refund amount.

## DoR checklist
- [ ] PO resolves shipping charge policy.

## Identity
Scope REF; identity FEAT-001.
