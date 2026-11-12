---
id: FEAT-001
type: feature
scope: REF
status: draft
bo: [BO-001]
---
## Goal
A buyer requests a return.
## Acceptance criteria
### AC-001-1 — Accepted parcel
Given a parcel delivered 5 days ago
When the buyer requests a return
Then status is "Awaiting inspection"
### AC-001-2 — Repeated request
Given a return already exists
When the buyer repeats the request
Then the response is fast
## Business rules
- One return per parcel. Example: parcel "PARCEL-A" cannot have two active returns.
## Non-functional
- Response time is below 900 ms under 80 concurrent buyers.
## UI/UX
None — this entry is handled by the support desk.
## Open questions
None
