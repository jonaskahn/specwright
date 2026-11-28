# Agent-first writing

Stories, epics, briefs, plans, tasks, cards and prompts are read by agents first. Write so an
agent can act without guessing and without spending tokens on filler.

## Rules
1. One fact per line. Short declarative sentences. Imperative for instructions.
2. Concrete values, not adjectives: "≤ 300 ms p95 at 50 rps", not "fast".
3. Name the actor, the input, the output. No pronouns with unclear antecedents.
4. Use IDs instead of restating: "per BR-002", not the rule text again.
5. No hedges: drop "should probably", "might", "ideally", "as needed", "if possible",
   "appropriate", "user-friendly", "etc.", "and so on", "various", "some".
6. No filler: drop "In order to", "It is important to note", "Basically", "Please".
7. Unknowns are explicit: `UNKNOWN` or a Q-NNN link. Never a vague placeholder or "TBD".
8. Lists over paragraphs when items are parallel. Tables for decision logic.
9. Keep required template sections. Write `None — reason` for an intentionally empty one.
10. Do not repeat across sections. The card summarises; the story holds the contract once.

## Words that need a number or a rule
fast, slow, large, small, many, few, soon, recent, secure, scalable, robust, simple, easy,
intuitive, flexible, reasonable, normal, standard, optimal, efficient.

## Check
`_shared/scripts/finish.py` runs `style_check.py` on the station's artifacts and reports each
hedge, filler phrase or unquantified word as a warning with file:line. Fix the line; do not
weaken the word list to hide a hit.

## Example
Before: "The system should ideally respond quickly and show an appropriate error if something
goes wrong with the payment."
After:
- Then the confirmation shows within 2 s (NFR-PERF-001).
- Then a declined card shows "Payment declined" and keeps the cart (AC-004-3).
