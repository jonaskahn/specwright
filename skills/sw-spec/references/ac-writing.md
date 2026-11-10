# Observable acceptance

Given describes an existing state; When names one event; Then describes an observable
result. And can extend a state or result without hiding a second scenario. These
are writing conventions, not syntax that automatically proves a requirement correct.
The kit keeps plain G/W/T text; no executable Gherkin dependency is needed.

Assign AC-<feature number>-<sequence>, such as AC-001-2. Keep existing numbers across
revisions. A removed criterion keeps a struck-through ID and withdrawal reason, with
a CR reference for published changes. Do not reuse it for a different behaviour.

Three useful refund examples:
1. Given delivered order R-240 worth 400,000 VND at age 6 days, When its owner requests
   a refund, Then one request is recorded as “Pending approval” for 400,000 VND.
2. Given an age-8-day order worth 400,000 VND, When its owner requests a refund,
   Then the pending request amount is 200,000 VND under BR-001.
3. Given an age-15-day order, When its owner requests a refund, Then no request is
   created and the agreed window-expired message is returned.

Three counterexamples:
- “Refunds are effortless and speedy.” Neither reviewer knows a pass threshold.
- “Given a customer presses a green control and types a value, When the page opens,
  Then the interface works.” Actions masquerade as state and the result is undefined.
- “All failures are handled correctly.” Enumerate known failures, their states and
  messages; do not promise an unbounded universe of outcomes.

Cover every rule row and each defined error. For BR-001, test ages 0, 7, 8, 14 and 15;
negative age is invalid delivery evidence, not a fourth refund tier. Decide whether
such input can occur and who rejects it before promising error behaviour.

A Scenario Outline and Examples table can compact repeated scenarios. Each row
substitutes concrete values for placeholders. Rule can group examples under one
business rule; avoid bloated shared Background assumptions. In Jira, make the
expanded expected outcomes understandable without Cucumber execution.

QA checks amount basis, currency rounding, calendar/time-zone convention, ownership,
prior requests and refusal messages. Missing decisions become Q records, not guesses.
Dev checks dependencies, observable state transitions and the intended approval
boundary. Acceptance of a request must not imply money has already been paid.

Method reference: https://cucumber.io/docs/gherkin/reference/
