# implementation terms

`L-015` flags implementation choices that leaked into requirement prose — a solution,
not a need. The checker matches these exact words in Goal, Acceptance criteria and
Business rules sections (and BO/BR cards).

## The list (as shipped in the checker)

sql, endpoint, microservice, kafka, redis, react, database table, json, http 500.

## Why it matters

Requirements describe what the actor needs and the observable result; the design owns
how. A "database table" in a business rule freezes an implementation the design has not
chosen. A story (BA/PO word) and a feature (Dev/QA word) are the same item written
FEAT-NNN — but its acceptance criteria stay design-free.

## How to resolve

Move the implementation choice to the design/design notes, and re-express the rule as
actor + observable outcome. Do not remove the word merely to silence the finding.
