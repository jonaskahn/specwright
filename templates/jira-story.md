---
id: FEAT-NNN
type: feature
scope: <SCOPE>
status: draft
jira_summary: "<Action and observable outcome, at most 100 characters>"
jira_issuetype: Story
jira_parent: <EPIC-KEY or None>
jira_labels: [specwright, feat:FEAT-NNN, proj:<SCOPE>]
jira_priority: <Medium>
bo: [BO-NNN]
---

## Goal
As a <role>, I want <capability> so that <measurable outcome>. Supports BO-NNN.

## Context
<Describe the current behavior, reason for change, and SRC-NNNN evidence.>

## Acceptance criteria
### AC-NNN-1 — <observable outcome>
Given <a concrete starting state>
When <a specific action occurs>
Then <the result a tester can observe>

### AC-NNN-2 — <alternative outcome>
Given <another concrete starting state>
When <a specific action occurs>
Then <the expected result>

## Business rules
- BR-NNN <rule and numeric boundary>. Worked example: <inputs and result>.

## Edge cases and error behavior
- IF <failure condition> THEN <visible message and resulting state>.

## Non-functional
- NFR-DOM-NNN: <metric, threshold, operating conditions, and measurement method>.

## UI/UX
- <Mockup URL or None — no UI>. Describe default, empty, loading, and error states.

## Out of scope
- <Excluded behavior> — reason: <why it is excluded>.

## Dependencies and relations
- <Relation and issue key, or None>.

## Open questions
None

## DoR checklist
- [ ] Goal identifies a business objective
- [ ] At least two criteria have concrete Given/When/Then examples
- [ ] Each business rule includes a worked example
- [ ] Non-functional limits have a measurement method
- [ ] UI states are described or explicitly not applicable
- [ ] Exclusions include reasons
- [ ] No unanswered questions remain
- [ ] Approval evidence names the approver and draft hash

## Identity
Spec ID: <SCOPE>:FEAT-NNN · Project: <SCOPE> · Repo card: <url> · Draft hash: <sha256:…> · Managed by specwright
