# Policy with examples

Keep a rule separate from its implementation. State the amount basis, boundary
inclusivity, dates and time zone, currency and rounding. Link the defining BR card and the
source decision. One worked example per rule is the minimum, not full coverage.

BR-001 candidate: elapsed local calendar dates 0..7 yield 100% of the whole-order paid
amount; 8..14 yield 50%; later dates refuse a refund. For a 1,200,000 VND order delivered
November 1 and requested November 10 (age 9), the refund is 600,000 VND. The local
calendar convention needs confirmation; keep Q-002 open until evidence exists.

## Decision tables

With two or more independent conditions, enumerate every combination. Illustration only;
do not mix it into BR-001 without approval:

| Within 30 days? | Unused item? | Result |
| --- | --- | --- |
| Yes | Yes | Full refund |
| Yes | No | Half refund |
| No | Yes | Store credit |
| No | No | Refuse |

- Confirm no gaps and no identical inputs with contradictory outputs.
- Label impossible combinations with reasons; never drop them silently.
- Compress rows with a don't-care value only when it cannot change the outcome.
- Map each row to an AC example or a named test input.
- Do not add a DMN hit policy to a small Markdown table.

## Conflicts and amendments

Conflicting source policies are a decision request, not an averaging exercise. Record who
chose which alternative, with evidence, in DEC/Q records. For an amendment, show current
and proposed rules in the CR and list every affected AC and test before changing numbers.
