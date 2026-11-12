---
id: FEAT-009
type: feature
scope: REF
title: Route a payment
aliases: []
status: draft
---
## Goal
A buyer pays a seller.

## Context
The cashier sends the payload after FEAT-002 accepts the order.

## Acceptance criteria
### AC-009-1 — Paid or refused
Given the buyer has 20 USD
When the seller accepts or the cashier refuses
Then the order is recorded as "Paid"

### AC-009-2 — Expired hold
Given the buyer left a hold of 20 USD
When the hold expires
Then the hold is deleted and the seller is notified

## Business rules
- Only the seller can accept. Example: a seller accepts 20 USD.

## Edge cases and error behavior
- IF the payload is empty THEN show "Missing amount".

## Non-functional
None.

## UI/UX
None.

## Out of scope
- Automatic reversal — reason: a later feature owns the payout.

## Dependencies and relations
FEAT-002 decides the order before payment.

## Open questions
None.

## DoR checklist
None.

## Identity
Spec ID: REF:FEAT-009
