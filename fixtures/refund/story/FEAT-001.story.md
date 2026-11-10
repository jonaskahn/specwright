---
id: FEAT-001
type: feature
scope: REF
title: Request a refund for a delivered order
status: draft
jira_summary: Request a refund for a delivered order
jira_issuetype: Story
jira_parent: None
jira_labels: [specwright, feat:FEAT-001, proj:REF]
jira_priority: Medium
bo: [BO-001]
br: [BR-001]
nfr: [NFR-REF-001]
sources: [SRC-0001, SRC-0002]
---
## Goal
As the customer who bought a delivered order, I want to lodge a refund request without support entering it, so that I can seek repayment without a support call. Business objective: BO-001.

## Context
SRC-0001 describes a 30-day policy; SRC-0002 proposes 14 days with two percentage tiers.
The example's Q-001 is resolved in favour of 14 days by DEC-001; production use requires
actual decision evidence, not this fixture. Finance still approves requests before payout.
Q-002 remains open for the calendar-day/time-zone convention; this draft is not ready.

## Acceptance criteria
### AC-001-1 — Request the full amount during the first week
Given customer C-100 owns delivered order ORD-1001 with a paid total of 1,200,000 VND and an agreed delivery age of 5 days
When C-100 submits a whole-order refund request for ORD-1001
Then one request is recorded in "Pending approval" for 1,200,000 VND

### AC-001-2 — Request half the amount in the second week
Given customer C-100 owns delivered order ORD-1002 with a paid total of 1,200,000 VND and an agreed delivery age of 10 days
When C-100 submits a whole-order refund request for ORD-1002
Then one request is recorded in "Pending approval" for 600,000 VND

### AC-001-3 — Refuse a request outside the window
Given customer C-100 owns delivered order ORD-1003 with an agreed delivery age of 15 days
When C-100 submits a whole-order refund request for ORD-1003
Then no request is recorded and the customer receives "The 14-day refund window for this order has ended."

## Business rules
- BR-001 Refund tiers on the whole-order paid total: ages 0–7 days yield 100%; ages 8–14 days yield 50%; ages greater than 14 days yield no refund.
  Example: an order paid at 1,200,000 VND with delivery date 2026-11-01 and request date 2026-11-10 has age 9 under the proposed local-calendar convention, giving 600,000 VND. This convention awaits Q-002.

| Delivery age | Requested amount | Creation outcome |
|---|---|---|
| 0 through 7 days inclusive | 100% of paid total | Pending approval |
| 8 through 14 days inclusive | 50% of paid total | Pending approval |
| More than 14 days | None | Refused |

## Edge cases and error behavior
- At day 7 the percentage is 100%; at day 8 it is 50%; at day 14 it is 50%; at day 15 no request is created (AC-001-1, AC-001-2, AC-001-3 boundary variants).
- Outside the window, return "The 14-day refund window for this order has ended." without creating a request (AC-001-3).
- Missing or invalid delivery evidence is outside this slice's valid delivered-order input contract; upstream validation must be confirmed during Dev review.

## Non-functional
- NFR-REF-001: refund submission p95 response time is below 2 seconds at 200 concurrent users, measured at the submission boundary during a 15-minute staging load test.

## UI/UX
- Mockups: None — interaction design is not agreed.
- States: default (eligible order), empty (no delivered orders), loading (submission pending), error (window-expired message). An accepted submission shows its pending approval state and amount.

## Out of scope
- Item-level refunds — allocation rules require separate analysis.
- Digital-goods refunds — the delivery-date basis does not apply.
- Automatic payout — finance approval remains mandatory outside this slice.

## Dependencies and relations
- Delivery evidence and customer ownership checks are existing prerequisites; confirm their contract with Dev before readiness.
- Decision and notification slices follow submission; no invented Jira keys or unallocated FEAT references are used here.

## Open questions
- [NEEDS CLARIFICATION: Q-002] Confirm whether age uses calendar dates in Asia/Ho_Chi_Minh or elapsed 24-hour periods. Until answered, boundary readiness is blocked.

## DoR checklist
- [x] Goal links BO-001.
- [x] Three concrete G/W/T criteria cover all refund tiers.
- [x] BR-001 includes a worked amount example.
- [x] NFR-REF-001 includes metric, threshold, conditions and measurement.
- [x] UI states and non-goals are explicit.
- [ ] Q-002 answered with evidence and day boundaries finalized.
- [ ] Dev confirms ownership and delivery-evidence dependencies.
- [ ] PO approval has a real evidence URL and matching hash.

## Identity
Spec ID: REF:FEAT-001 · Project: REF · Repo card: FEAT-001.card.md · Draft hash: sha256:e416243ab3d3b5692c5ab9a0ed8b3154bffa445aa7844ea6cc35ff45f4f3ce7b · Managed by specwright
Dev consumer check: AC-001-1/2/3 no — confirm input contract and Q-002 before implementation.
QA consumer check: AC-001-1/2/3 no — numeric outcomes are concrete but calendar boundaries await Q-002.
