# sw-craft — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

1. Resolve scope before writing: explicit argument, qualified ID, project path, flat
   manifest, then ask. Never use a program default to guess a write scope. Read named
   material and existing Q/DEC records before asking anything.
2. Pick the mode. Pasted material: synthesize it at once into a provisional brief,
   separating sourced facts, proposals and unknowns; do not restart an interview. Sparse
   idea: ask only the highest-impact unanswered questions.
3. Frame the brief with references/idea-method.md; fill assets/idea-brief.md. Include
   actor context, observed problem, smallest outcome, at least three non-goals with
   reasons, falsifiable assumptions, and risks (impact, likelihood, owner, response) in the brief's Risks section; no shipped script
   creates separate RISK cards.
4. Choice that changes scope: use references/question-bank.md. Ask at most five ranked
   questions per batch, each with options, consequences and an explicit unanswered
   default. Record each question at once with `record.py q new --status proposed`
   (title, `--affects`, `--owner`, the cited lines) and each answer with `q answer`.
   A default is not human approval.
5. Run scripts/leakage.py <brief> on the Problem and Smallest valuable outcome sections.
   Exit 0 clean; 1 rewrite the reported file:line passages; 2 fix the invocation.
   Rerun until clean, then read both sections for leakage the word list cannot detect.
   Never weaken the list to hide a hit; word-list changes (references/leakage-words.md)
   are a separate edit.
6. Propose feature slices with references/invest.md. Each gets a verb-first title, one
   principal actor, a valuable outcome, and a row in the INVEST table (scripts/invest.py
   check): I/N/V/E/S/T each pass, fail or unknown, a Reason when not all pass. Do not allocate FEAT IDs yet; state hard
   dependencies.
   Name the business objective or objectives the epic serves (`--bo BO-001`, repeat for more,
   `ORD:BO-001` for another project's), taken from the idea's evidence; when the evidence does not
   say, raise a question and leave `bo:` empty, never invent one. Run scripts/new_epic.py
   (template assets/epic.md) only when an empty epic must exist before the split is accepted;
   otherwise step 7 creates it with `accept-split --new-epic --bo BO-001`. Change them later with
   `new_epic.py --set-bo EPIC-001 --bo BO-002`.
7. Get the owner's acceptance of the split. Only then run `record.py accept-split`
   (`--dry-run` first): it reserves the FEAT IDs (the next number skips every historical
   or withdrawn ID), keeps each legacy ID as an alias, creates or fills the epic and
   writes one DEC, all in one logged step. With `signoff: optional` omit the decider
   flags: it records the owner (self) with session evidence. With `signoff: required`
   pass the approver's role and name and an https evidence URL (exit 3: set up
   approvers). Without acceptance keep the proposals as drafts with an open Q.
   See _shared/references/governance.md.

## Existing baseline

When the project already runs capabilities under its own IDs, start from its legacy register, not
from an idea: scripts/baseline.py import-register, propose-grouping, then per group reserve
(each legacy ID stays an alias; provisional, not an accepted split) and brief (one brief and a
first question: keep each legacy item as one feature or re-split by INVEST). The PO's decision
is recorded with `record.py accept-split --from-register <group>`.

## Consumer check

Could Dev estimate each slice, and could QA describe one observable success and one
failure? For each "no", record the concrete gap instead of declaring INVEST passed.

## Stop and ask

Ask only what sources do not settle, per `_shared/references/stop-and-ask.md`. A safe default is
"leave unresolved; no ID reservation".

## Gotchas

- A widget is not a problem; naming an API is not a business outcome.
- An actor's current tool belongs in Actors, not in the solution-free Problem.
- Pasted proposals mix useful evidence with an unapproved solution; separate them.
- A clean word scan proves neither absence of design leakage nor INVEST quality.
- Neither an unanswered default nor a confident synthesis can authorize a split.
