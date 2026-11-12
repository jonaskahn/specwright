# Observable acceptance

Given = an existing state. When = one event. Then = an observable result. `And` extends a
state or result without hiding a second scenario. Use plain G/W/T text; no executable
Gherkin dependency.

## Layout

Write each criterion as a bulleted list, one step per line, with the keyword in bold. A
continuation step is its own bullet with a bold `And` or `But`:

    ### AC-001-1 — Refund inside the window

    - **Given** delivered order R-240 worth 400,000 VND at age 6 days
    - **When** its owner requests a refund
    - **Then** one request is recorded as "Pending approval" for 400,000 VND
    - **And** the owner sees the request number

Never run the three steps together in one paragraph. Older stories that write bare
`Given`, `When`, `Then` lines still pass lint, the card, the Gherkin export and the illustration
count; when you amend one, put its criteria in this layout.

## IDs

`AC-<feature number>-<sequence>`, for example AC-001-2. Keep numbers across revisions. A
removed criterion keeps a struck-through ID and a withdrawal reason (plus a CR reference
for published changes). Never reuse it for different behaviour.

## Good examples

1. Given delivered order R-240 worth 400,000 VND at age 6 days, When its owner requests a
   refund, Then one request is recorded as "Pending approval" for 400,000 VND.
2. Given an age-8-day order worth 400,000 VND, When its owner requests a refund, Then the
   pending request amount is 200,000 VND under BR-001.
3. Given an age-15-day order, When its owner requests a refund, Then no request is created
   and the agreed window-expired message is returned.

## Bad examples

- "Refunds are effortless and speedy." No pass threshold.
- "Given a customer presses a green control and types a value, When the page opens, Then
  the interface works." An action posing as state; undefined result.
- "All failures are handled correctly." Enumerate each known failure, its state and message.

## Coverage

Cover every rule row and each defined error. For BR-001 test ages 0, 7, 8, 14 and 15. A
negative age is invalid delivery evidence, not a fourth tier: decide whether it can occur
and who rejects it before promising error behaviour.

A Scenario Outline with an Examples table compacts repeated scenarios; each row
substitutes concrete values. Group examples under one rule with `Rule`; avoid bloated
shared `Background`. In Jira, make expanded outcomes readable without Cucumber.

## Dev and QA checks

- QA: amount basis, currency rounding, calendar and time-zone convention, ownership,
  prior requests, refusal messages. A missing decision becomes a Q record, not a guess.
- Dev: dependencies, observable state transitions, the approval boundary. Accepting a
  request never implies money has been paid.

Reference: https://cucumber.io/docs/gherkin/reference/
