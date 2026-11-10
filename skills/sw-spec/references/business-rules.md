# Policy with examples

Keep a rule separate from its implementation. State the amount basis, inclusivity of
boundaries, dates/time zone, currency and rounding. Link its defining BR card and
source decision. One worked example per rule is the minimum, not complete coverage.

BR-001 candidate: elapsed local calendar dates 0..7 yield 100% of the whole-order
paid amount; 8..14 yield 50%; later dates refuse a refund. For a 1,200,000 VND order
delivered November 1 and requested November 10, age 9 means 600,000 VND. The local
calendar convention needs confirmation; keep Q-002 open until there is evidence.

With two independent conditions, enumerate combinations. This alternative practice
policy is illustrative and must not be mixed into BR-001 without approval:

| Within 30 days? | Unused item? | Result       |
|-----------------|--------------|--------------|
| Yes             | Yes          | Full refund  |
| Yes             | No           | Half refund  |
| No              | Yes          | Store credit |
| No              | No           | Refuse       |

Two binary conditions have four combinations. Confirm there are no gaps and no
identical inputs with contradictory outputs. Explicitly label impossible combinations
with reasons instead of silently dropping them. A don't-care value can compress
rows only when it cannot change the outcome. Each row should map to an AC example
or named test input. Do not introduce an unverified DMN hit policy merely to label
a small Markdown table.

Treat conflicting source policies as a decision request, not an averaging exercise.
Record which authority chose which alternative and its evidence in DEC/Q records.
For amendments, show current and proposed rules in the CR and identify all affected
ACs and tests before changing the numbers.
