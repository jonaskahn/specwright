# Ready for a human review

Keep every heading from the story template even when it holds “None — reason”.
Before requesting review, check:

- Goal names a contextual actor, capability, benefit and resolving BO reference.
- At least two ACs have concrete G/W/T examples. A catalogue import is sized by
  `compile_story.py split` (target 3–7 criteria, one actor and one screen). Every rule
  branch and error row is covered, including boundary inputs. Withdrawn IDs remain tombstoned.
- Rules contain key numbers and worked examples. NFRs state conditions and method.
- UI states are named, or no-UI scope is explicit. Every supplied mockup, Figma link, screenshot
  or diagram is listed in `assets:` and in the UI/UX Visuals list. Out-of-scope items have reasons.
- Dependencies are actual references, not invented IDs. Cross-scope IDs are qualified.
- Open questions are resolved for readiness, with decisions and evidence retained.
- Dev and QA checks say yes per AC, with an explanation, or the draft stays blocked.
- The card fits its limits and does not carry a second copy of acceptance criteria.
- Review lint passes. Approval is later recorded only through sw-craft: the owner's accept
  (`signoff: optional`) or, under `signoff: required`, a sign-off with role, name, date,
  evidence URL and the exact approved draft hash.

INVEST (independent value, negotiable solution, estimable, team-confirmed size,
observable tests) is a useful check, not a substitute for PO approval. A draft can be
complete and still unapproved.

Published amendments need a current Jira snapshot and a real CR. Inspect approval
freshness after every behaviour change. A previous approval of different content
cannot be carried forward just because the FEAT ID stayed the same.

The draft hash lives in front matter (`draft_hash`) and is excluded from the hash, like the
old Identity section. Readiness is `features/FEAT-NNN/review/dor.md`, not a section of the
story. Do not hide behaviour, rules or readiness decisions outside the hashed story body.
