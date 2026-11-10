# rule catalog

`scripts/sw_lint.py` checks decidable contracts; wording quality stays a human judgment.
Each finding prints `path:line: L-NNN message`. Choose the gate by what must be true next.

## Gates

| Gate | Exit | Blocks when |
| --- | --- | --- |
| `draft` | 10 | shape and measurable rules fail |
| `review` | 20 | sign-off and DoR fail (default) |
| `publish` | 30 | the publish contract fails |
| `sync` | 40 | the drift contract fails |

Exit `0` is a pass; `2` is usage or an unexpected checker failure. No network is used.

## Rule families

- **Front matter and identity** — `L-001`/`L-002` (name, ID grammar), `L-003`
  (duplicate ID), `L-016` (invalid status), `L-043` (scope, Jira key, https, refs).
- **Acceptance criteria** — `L-005` (BO reference), `L-007` (Given/When/Then order),
  `L-008` (observable literal), `L-009` (ambiguous pronoun or unqualified "secure"),
  `L-014` (clarification markers), `L-017` (numbered AC heading).
- **Business rules and NFRs** — `L-010` (metric, threshold, condition), `L-011`
  (worked example), `L-012` (UI states), `L-013` (exclusions with reason).
- **Leakage and weak words** — `L-015` (implementation choice in requirements),
  `L-009` vague words, `L-024` (card/word cap).
- **Publish contract** — `L-018` (open questions resolved), `L-037`, `L-045`, `L-046`.
- **Snapshot and drift** — `L-038` (snapshot sections), `L-039` (contract checks),
  `L-041`/`L-042` (published draft changed without a CR), `L-044` (Jira status mapping).

Never weaken a rule, banned word or threshold to make a report pass. A waiver, where the
gate supports one, is recorded — not invented.
