---
name: sw-spec
description: Writes or amends feature story drafts and compact cards with concrete Given/When/Then criteria, worked business rules, measurable NFRs and Dev/QA checks, and draws story diagrams. Use when asked to spec an accepted FEAT, add a boundary criterion, revise a story, draw a story diagram, apply a recorded CR, or spec several reserved features at once (one parallel worker each). Do NOT use for shaping an unaccepted idea (use sw-shape) or publishing a draft (use sw-publish).
---

# sw-spec

Write the story contract: concrete criteria, worked rules, measurable NFRs, a picture when needed.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`02-drafts/FEAT-NNN.story.md` and card, `diagrams/`, draft BR/NFR/FR cards, Q records and
reservations via scripts, RTM draft columns via the trace capability.

## Steps

1. Resolve scope. Unaccepted idea → sw-shape. Run `_shared/scripts/graph.py context FEAT-NNN`;
   read its answers, decisions and sources. Cite with `cite.py stamp`.
2. New: `scripts/new_story.py --scope-root <project> --scope <S> --reserved FEAT-NNN`.
   Resume: edit the draft. Published story: stop unless a current snapshot and a CR exist.
3. Visual references: `graph.py neighbors FEAT-NNN --dir in --rel supports` (and its epic);
   list each ASSET in `assets:` and UI/UX Visuals with the AC it shows.
4. Fill all twelve sections in template order; empty → `None — <reason>`. ≥ 2 ACs, each
   `- **Given** / **When** / **Then**` with concrete values; happy path, every rule branch,
   boundaries, errors. Rules: key numbers + one worked example; NFR: metric, threshold, load,
   method. AC IDs never reused. Set `links:` to ≥ 1 https URL (source page, tracker or design);
   the card copies it and lint L-040/L-043 require it.
5. `scripts/illustration_check.py FEAT-NNN` and act on the chip (`references/illustration-need.md`).
6. Unknowns → Q records; ≤ 3 `[NEEDS CLARIFICATION: Q-NNN]` markers. Non-blocking → assumed Q.
7. Before an accepted change to an existing draft: `record.py backup 02-drafts/<file>`.
8. `scripts/spec_hash.py --scope-root <project> --stamp FEAT-NNN`; `scripts/card_gen.py <story>`.
9. Several reserved features → one worker per FEAT (`references/parallel-spec.md`).

## Stop when

Ambiguous scope; amendment without CR or snapshot; a blocking question; conflicting policy.

## Finish

Run `_shared/scripts/finish.py --skill sw-spec --subject "<FEAT-NNN> story" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit; a clean draft is submitted to review by the hand-off, not by editing its status). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Writing ACs | references/ac-writing.md; references/ears.md |
| Rules, decision tables | references/business-rules.md |
| NFR thresholds | references/nfr-defaults.md |
| Drawing (chip says needs or check) | references/illustration-need.md; references/type-picker.md |
| Several features at once | references/parallel-spec.md |
| Gherkin export | scripts/export_feature.py --help |
| A step above is unclear or a script errors | references/procedure.md |
