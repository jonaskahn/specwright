## Goal
Allow a billing clerk to refund a settled payment, supporting BO-001.

## Acceptance criteria
### AC-001-1 — Full refund
Given a settled payment of 40 USD
When the clerk confirms a refund of 40 USD
Then the refundable balance becomes 0 USD

### AC-001-2 — Reject excess amount
Given a refundable balance of 40 USD
When the clerk requests 41 USD
Then the balance stays 40 USD and the message is **Amount exceeds balance**

## Business rules
- BR-001: Refunds cannot exceed the remaining balance.
- [ ] Record the refund reference

## Context
Read [the **billing** policy](https://example.test/policy).
Literal \* characters remain literal.  
This line follows a hard break.

| Input | Result | Note |
| --- | --- | --- |
| 40 USD | 0 USD |  |
| 41 USD | 40 USD | Use `a|b` |

## Identity
Spec ID: REF:FEAT-001 · Project: REF · Draft hash: sha256:example · Managed by specwright
