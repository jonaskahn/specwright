---
id: FEAT-005
type: feature
scope: REF
title: Share a thread
aliases: []
status: draft
---
## Goal
A buyer and a seller share a thread.

## Context
The thread is visible to both.

## Acceptance criteria
### AC-005-1 — Open
Given the buyer is present
When the seller opens the thread
Then both see the thread

### AC-005-2 — Quiet
Given the thread exists
When the buyer reads it
Then the thread shows "quiet"

## Business rules
A thread has one subject. Example: "returns".

## Edge cases and error behavior
- IF the seller is absent THEN show "Seller unavailable".

## Non-functional
None.

## UI/UX
None.

## Out of scope
- File attachments — reason: the thread carries text only.

## Dependencies and relations
None.

## Open questions
None.

## DoR checklist
None.

## Identity
Spec ID: REF:FEAT-005
