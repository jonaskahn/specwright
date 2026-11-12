---
id: FEAT-004
type: feature
scope: REF
title: Note a preference
aliases: []
status: draft
---
## Goal
A buyer saves a colour preference.

## Context
The preference stays with the account.

## Acceptance criteria
### AC-004-1 — Save
Given the buyer is signed in
When the buyer chooses "blue"
Then the preference is recorded as "blue"

### AC-004-2 — Read
Given the preference is "blue"
When the buyer opens the account
Then the account shows "blue"

## Business rules
The preference is a named colour. Example: "blue".

## Edge cases and error behavior
None.

## Non-functional
None.

## UI/UX
None.

## Out of scope
- Sharing the preference — reason: one account holds it.

## Dependencies and relations
None.

## Open questions
None.

## DoR checklist
None.

## Identity
Spec ID: REF:FEAT-004
