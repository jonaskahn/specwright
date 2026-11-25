---
name: sw-shape
description: Shapes an early proposal into a problem-led idea brief and a split into independent, testable features (INVEST). Use when asked to shape an idea, separate outcomes from a proposed interface, split an epic, or decide whether a capability is one story or several. Do NOT use for writing acceptance criteria or story drafts (use sw-spec).
---

# sw-shape

Turn an idea into a problem-led brief and an accepted INVEST feature split.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`01-analysis/ideas/` brief, `01-analysis/` BO/STK drafts, records and reservations only via
`_shared/scripts/record.py` (`--dry-run` first).

## Steps

1. Resolve scope. Read named sources and existing Q/DEC first.
2. Pasted material → synthesize a provisional brief at once. Sparse idea → ask only the
   highest-impact gaps (`references/question-bank.md`, ≤ 5, each saved with `record.py q new`).
3. Fill `assets/idea-brief.md`: actors, problem, smallest outcome, ≥ 3 non-goals with reasons,
   falsifiable assumptions, risks (impact, likelihood, owner, response). No technology.
4. `scripts/leakage.py <brief>` until exit 0; then reread Problem and Outcome for leakage.
5. Propose slices: verb-first title, one actor, one outcome, INVEST row each
   (`scripts/invest.py check`). Name the epic's BO from evidence, else raise a Q. No FEAT IDs yet.
6. Ask the owner to accept the split (this is the stop). On yes:
   `record.py accept-split --dry-run`, then run (`--new-epic`, `--bo`, decider flags only under
   `signoff: required`).

## Stop when

Split acceptance; a scope-changing choice; leakage that needs the owner's wording.

## Finish

Run `_shared/scripts/finish.py --skill sw-shape --subject "<IDEA or EPIC ids> shaped" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Brief technique | references/idea-method.md |
| Slicing rules | references/invest.md |
| Legacy register as input | references/procedure.md (Existing baseline); scripts/baseline.py --help |
| Empty epic before acceptance | scripts/new_epic.py --help; assets/epic.md |
| Leakage word list | references/leakage-words.md |
| A step above is unclear or a script errors | references/procedure.md |
