---
id: IDEA-refunds
type: idea
scope: REF
title: Customer refund access
status: draft
home: repo
sources: []
---
## Frame
Customers need to request refunds for delivered orders without a support call.

## Actors
Customer with a delivered order; currently calls support to enter a request. Example evidence: SRC-0002.

## Problem
Customers need a green button that calls the payments API.

## Smallest valuable outcome
A customer can lodge an eligible whole-order request and learn its amount pending approval, without support entering it.

## Non-goals
- Item-level refunds — reason: separate allocation rules.
- Digital goods — reason: no delivery-date basis.
- Automated payout — reason: finance approval stays separate.

## Ranked questions
1. Q-001 [blocking]: 14 or 30 days? A) 14 → Legal amends conflicting policy; B) 30 → tiers need revision; C) defer → no approved rule. Default: defer. Owner: PO.
2. Q-002 [blocking]: calendar days or elapsed hours? A) calendar → midnight boundaries; B) elapsed → timestamp dependence. Default: leave boundary approval blocked. Owner: PO.

## Assumptions
We believe support entry is the obstacle; false if fewer than 26 of 50 sampled cases need support entry by an agreed review date (date still unknown).

## Risks
RISK-001 (proposed): conflicting windows risk incorrect amounts; likelihood unknown; PO owns policy reconciliation before approval.

## Proposed FEAT split
Proposal: Lodge a refund request — customer gains pending request with calculated amount.
- I pass: existing finance process can consume it
- N pass: no interface is prescribed
- V pass: avoids support entry
- E unknown: window and day counting unresolved
- S unknown: team estimate needed
- T pass: amount and state observable
Proposal: Decide a refund request — finance gains approval or refusal recorded.
- I fail: needs an existing request
- N pass: review interface remains open
- V pass: records payout authority
- E unknown: approval limits need evidence
- S unknown: variants need sizing
- T pass: decision and approver observable
Proposal: Notify the requester — customer gains receives decision.
- I fail: needs recorded decision
- N pass: channel remains negotiable
- V pass: customer learns outcome
- E unknown: retry expectations missing
- S unknown: team estimate needed
- T pass: recipient and decision verifiable
No FEAT IDs reserved until PO accepts the split with evidence.

## Design-leakage self-check
Problem and outcome avoid interface and technology choices. Re-run leakage.py and review meaning before acceptance.
