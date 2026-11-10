# Candidate extraction and conflict review

Read the snapshot, not an imagined source. Record SRC id, line range, version
and a short quotation beside each candidate. Separate direct statements,
interpretations and unanswered questions.

- Stakeholders: role, activity, business context and systems; prefer roles to
  personal contact details.
- Objectives: outcome and measurable evidence, not assumed implementation.
- Rules: quantities, units, time origin, inclusivity, rounding, exceptions, owner.
- Non-functional hints: load, response time, accessibility, retention and auditing;
  adjectives without thresholds remain questions.
- Vocabulary: aliases and ambiguous terms that could change a rule's meaning.
- Legacy material: unknown upstream links are untraced; never invent ids.

## Detect conflicts manually

Compare new claims with relevant sources and analysis cards. Normalize units for
comparison but retain original wording. Check the same actor/action with different
numbers, dates, eligibility or exceptions. Different contexts may not conflict:
first establish whether both govern the same event. A newer date alone does not
establish authority. Create a Q- record instead of silently changing a rule.
Allocate Q ids from records and registry without reusing withdrawn ids.

Minimal record; replace bracketed values with real evidence:

~~~markdown
---
id: Q-001
type: q
status: open
sources: [SRC-0001, SRC-0002]
---
# Refund window: 14 or 30 days?
Question: Which window applies after delivery?
Why it matters: eligibility and refund tiers change.
Evidence: SRC-0001, lines [range]: "[exact policy quotation]"
Evidence: SRC-0002, lines [range]: "[exact email quotation]"
A: 14 days; Legal must revise the 30-day policy.
B: 30 days; tier boundaries need a new PO decision.
C: 14 days in product plus a 30-day support exception; adds manual handling.
Owner: [responsible role and person, or UNKNOWN]
Due: [agreed date, or UNKNOWN]
Status: open
Answer: UNKNOWN; once answered link evidence and DEC id.
Affected IDs: [existing candidate rule ids, or UNKNOWN]
~~~

The refund fixtures disagree: policy says 30 days after delivery; email says
14 days, full refund in the first week and half afterward. Keep both citable;
do not approve either BR until the PO answers. Cards require user acceptance;
keep at most three explicit clarification markers per card, splitting if needed.
