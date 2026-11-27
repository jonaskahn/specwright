---
name: sw-craft
description: Creates sources, as-is analysis, idea briefs, feature stories, diagrams and tasks, then reviews them for owner acceptance. Use when importing sources, analysing behaviour, shaping ideas, writing or changing stories, splitting tasks, drawing diagrams, or reviewing FEAT-001. Runs intake through review unless a station is named. Do NOT use for implementation plans (use sw-forge), Jira publishing (use sw-ship), or writing code.
---

# sw-craft

The BA role. One skill, five phases: intake → as-is → shape → story and tasks → review.
Accept things no further than the finalize; hand the plan to sw-forge only when the user asks.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`00-inbox/` snapshots and raw copies, `01-analysis/` (ideas, as-is, epics), `02-drafts/`,
`03-plan/FEAT-NNN.tasks.md`, `diagrams/`, `records/` and reservations only via
`_shared/scripts/record.py` (`--dry-run` first), registry rows and RTM columns via scripts.

## Steps

0. Run `scripts/analyze.py roots` when any phase below needs code. Detected, unregistered
   roots → list them, ask once, then `roots --add <path> ...`. No code anywhere is fine: the
   actual side of an analysis is empty. Also `_shared/scripts/stack.py show`; missing with code
   → `_shared/scripts/stack.py detect --write`, show the layers and ask once, lock on yes
   (`_shared/scripts/stack.py lock --confirm <hash shown>`). The story step reads the same profile.
1. **Intake** (idea text, or files/Jira/email). Resolve scope. Convert with
   `scripts/to_md.py <file> --out <project>/00-inbox/`; multiple files → `scripts/bulk_import.py
   --batch-id <id> --dry-run`, then run. Scan each snapshot: `scripts/secrets_scan.py
   <snapshot>`; exit 1 → redact a copy (`--redact --out`) and ingest it with
   `--redacted-from <sha256>`. Extract candidate facts and conflicts; a conflict becomes a Q
   record quoting both sources (`record.py q new --raised-from SRC-…`) — never a winner.
   Changed logic in a story → `scripts/impact.py` saves a proposed CR. No requirement edit.
2. **As-is** (code exists, or the request changes, fixes or completes existing behaviour).
   No `inventory.md`, or the user wants an overview → `scripts/analyze.py inventory`; show the
   top candidates, let the user pick. Import missing intended sources first (intake). Then
   `scripts/analyze.py area <keywords>`, read only the listed files (docs first, then code and
   tests, `references/method.md`), and `scripts/analyze.py new <FEAT-NNN|slug>`. One Criteria
   row per observable behaviour; cite code with `scripts/analyze.py cite <root>/<path> --lines A-B`.
   Code-only behaviour: Intended = `observed`. Sources disagree → `divergent` plus a Q.
3. **Shape.** Read named sources and existing Q/DEC first. Pasted material → a provisional
   brief at once; a sparse idea → ask only the highest-impact gaps
   (`references/question-bank.md`, ≤ 5, each saved with `record.py q new`). Fill
   `assets/idea-brief.md`: actors, problem, smallest outcome, ≥ 3 non-goals with reasons,
   falsifiable assumptions, risks. No technology. `scripts/leakage.py <brief>` until exit 0,
   then reread Problem and Outcome for leakage. Propose slices: verb-first title, one actor,
   one outcome, INVEST row each (`scripts/invest.py check`). Name the epic's BO from evidence,
   else raise a Q. No FEAT IDs yet. **Ask the owner to accept the split — this is a stop.**
   On yes: `record.py accept-split --dry-run`, then run (`--new-epic`, `--bo`, decider flags
   only under `signoff: required`).
4. **Story and tasks.** An unaccepted idea goes back to Shape, above. Existing behaviour → read
   `references/change-fix.md` first (wording changes of a published story: `assets/cr.md`).
   `_shared/scripts/graph.py context FEAT-NNN`; cite with
   `cite.py stamp`. New → `scripts/new_story.py --scope-root <project> --scope <S> --reserved
   FEAT-NNN`; resume → edit the draft. A published story is never edited in place: open a
   `CR-NNN` instead (`references/change-fix.md`). Visual references: `graph.py neighbors
   FEAT-NNN --dir in --rel supports`; list each ASSET in `assets:` and in UI/UX Visuals with
   the AC it shows. Fill all twelve sections in template order; empty → `None — <reason>`.
   ≥ 2 ACs, each Given/When/Then with concrete values; rules with one worked example; NFRs
   with metric, threshold, load, method; `links:` with ≥ 1 https URL.
   `scripts/illustration_check.py FEAT-NNN`; unknowns → Q records; ≤ 3
   `[NEEDS CLARIFICATION: Q-NNN]` markers; `record.py backup 02-drafts/<file>` before an
   accepted change. `scripts/spec_hash.py --scope-root <project> --stamp FEAT-NNN`;
   `scripts/card_gen.py <story>`.
   Then `03-plan/FEAT-NNN.tasks.md` (`references/task-format.md`): `TASK-<n>-<k>`, one `[layer]`
   prefix, one outcome. Fields: Traces to (≥ 1 AC), Stack (from `stack.py show`), Visuals (UI
   tasks when the story has visuals), `Touches: <code-root>/<path>` or `Touches: new:<path>`
   for a folder that does not exist yet, Depends on, Done when, Stop and ask if, and
   `Status: not-started`. Copy the story's `Draft hash` to `spec_hash`; coverage and the plan
   are checked by sw-forge.
5. **Review (automatic).** No feature named → every row of `graph.py board --station review
   --format json`. Machine gates first: `_shared/scripts/sw_lint.py --gate review`, DoR; a
   failing gate sends the item back to the story step. Then the independent review
   (`references/debate.md`):
   `scripts/debate.py brief` and `start`; run the three reviewers (critic, builder, tester) as
   separate subagents given only the brief; record their rows, answer each as the author
   (`accepted` → fix the draft, `rebutted` → evidence, `open` → Q record); round 2 seals and
   checks. Under a builder profile debate is off by default; only the hash confirm remains —
   the gate is never skipped. Show `scripts/debate.py pack`, then ask once for the batch:
   "Finalize FEAT-001 (hash …)? — yes / send back with notes / answer Q-…". On the yes:
   `scripts/review.py accept --draft <file> --scope-id <S> --manifest <m> --hash <hash shown>`
   (it refuses without a passing debate check; `--skip-debate "<reason>"` is recorded).
   `signoff: required`: `verify`, then `promote`. A changed draft after the finalize opens a
   fresh round; the old hash never carries over.

## Change requests

A story that was never published is edited in place. A published story changes only through a
`CR-NNN` record (`assets/cr.md`): `base_hash` of the target, a Delta table, Must not change,
and the wording. `scripts/merge.py base|check` keep it true. Apply it with `scripts/merge.py
ship` once every AC row verifies; `scripts/merge.py finish` copies the wording, bumps the
target version and returns it to review.

## Stop when

Split acceptance, the finalize, a scope-changing choice, ambiguous
scope, a blocking question, registration of code roots, sensitive retention, leakage that
needs the owner's wording, an uncurrent CR. The hand-off to sw-forge is never automatic.

## Finish

Run `_shared/scripts/finish.py --skill sw-craft --subject "<what changed>" --cwd <project>`.
Follow `_shared/references/handoff.md` for item selection, limits and every `handoff.mode`.
On `done`: Report accepted stories and tasks. Say "Say **forge** to plan FEAT-001." Never load sw-forge automatically.

## Load only when

| Need | File |
| --- | --- |
| Brief questions, brief technique, slicing | references/question-bank.md; references/idea-method.md; references/invest.md |
| Leakage word list | references/leakage-words.md |
| Empty epic before acceptance; legacy register | scripts/new_epic.py --help; scripts/baseline.py --help; assets/epic.md |
| Importing: converter routes, limits, exit codes | references/router.md; scripts/wiki_pull.py --help |
| Candidates, conflicts, multiple snapshots | references/extraction-checklist.md; references/parallel-work.md; references/candidate-contract.md; scripts/candidates.py --help |
| More than one epic or feature; what can run in parallel | references/layered-writing.md |
| Secrets or personal data | references/pii-policy.md |
| Mockups, links, images in a batch | _shared/references/capabilities/assets.md |
| Remote read tools | _shared/references/capabilities/remote.md |
| How to read code for behaviour, statuses, confidence | references/method.md |
| Writing ACs, rules, NFR thresholds | references/ac-writing.md; references/ears.md; references/business-rules.md; references/nfr-defaults.md |
| Drawing (chip says needs or check) | references/illustration-need.md; references/type-picker.md; the chosen references/type-<kind>.md |
| Source provenance, original bytes | scripts/provenance.py --help |
| Gherkin export; diagram render and embed | scripts/export_feature.py --help; scripts/render_diagram.py --help; scripts/embed_diagram.py --help |
| Foundation story (structure, lint, format, coverage, CI, AGENTS.md) | _shared/references/foundation.md; _shared/scripts/foundation.py --help |
| Version 1, change, fix, ship, merge, CR | references/change-fix.md; scripts/merge.py --help; scripts/cr.py --help |
| Debate roles, rounds, severity, independence | references/debate.md |
| Formal sign-off evidence | references/approval-evidence.md |
| Gate table by sign-off mode | _shared/references/governance.md |
| Several features in one station | _shared/references/parallel-writers.md; references/parallel-spec.md |
| Hand-off details, stop rules; transitions | _shared/references/handoff.md; _shared/references/lifecycle.md |
| A step above is unclear or a script errors | references/procedure.md; references/story-procedure.md; references/review-procedure.md; references/ingest-procedure.md; references/analyze-procedure.md |
