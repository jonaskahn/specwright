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
Never allocate a Q id by hand: `record.py` does it from records and registry and never reuses
a withdrawn id. Save the conflict with:

```sh
_shared/scripts/record.py q new --title "Refund window: 14 or 30 days?" --owner <role> \
  --affects <FEAT-NNN> --raised-from SRC-0001:L12-L14 --raised-from SRC-0002:L3 \
  --quote "<exact words from the cited lines>" --option "14 days -> <consequence>" --option "30 days -> <consequence>"
```

The record follows `assets/q.md` (Question, Why it matters, Options, Owner, Due, Status, Answer,
Decision link). State each option with its consequence, for example
`--option "14 days -> Legal must revise the 30-day policy"` and
`--option "30 days -> tier boundaries need a new PO decision"`; do not pick a winner.

Example conflict: policy says 30 days after delivery; an email says 14 days, full refund in
the first week and half afterward. Keep both citable; approve neither BR until the PO
answers. Cards need user acceptance. Keep at most three clarification markers per card;
split the card if more are needed.
