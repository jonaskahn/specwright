# INVEST and useful slices

INVEST names six discussion tests introduced by Bill Wake. It does not make story
quality mechanically decidable. Record one reason per letter for every proposed FEAT:

| Letter | Test | Refund submission example |
|---|---|---|
| I — Independent | Can it deliver value without a jointly released slice? | Pass: request can await an existing finance process. |
| N — Negotiable | Is behaviour fixed while solution choices remain open? | Pass: submission channel is not prescribed. |
| V — Valuable | Does a named actor gain a useful outcome? | Pass: customer no longer needs support to lodge a request. |
| E — Estimable | Are major rule uncertainties bounded enough for Dev? | Unknown: delivery-day calculation still needs a decision. |
| S — Small | Can the team finish and verify it within its agreed delivery window? | Unknown until the team estimates it. |
| T — Testable | Can QA observe success and refusal with concrete inputs? | Pass: amount and pending state are observable. |

A local heuristic of about seven or fewer ACs can prompt a size conversation; it is
not Wake's definition and not proof that a story fits a team's capacity. Negotiability
and estimability require human judgement. Do not turn “unknown” into “pass”.

Split by workflow step when each step still has user value: lodge a refund, decide
it, notify the requester. Split by rule variant if a subset is independently useful;
by happy versus exceptional path only if leaving the exception out is safe; by data
type or role when each group can genuinely use its result. Keep critical rejection
behaviour with submission rather than shipping an unsafe happy-only feature.

Avoid horizontal slices such as database, endpoint, and page: each may need the
others before the customer receives value. If a dependency cannot be removed, state
it and show which existing capability or later FEAT supplies it. Never invent links.

Source for method facts: https://xp123.com/invest-in-good-stories-and-smart-tasks/
Examples and local heuristics here are kit guidance, not quotations.
