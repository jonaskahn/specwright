---
name: sw-forge
description: Turns an accepted story and its tasks into a very detailed, ready-to-apply implementation plan — exact files per task, the change itself, the test that proves it and the command that runs it — then writes one self-contained prompt per task and moves every task from not-started to planned. With no feature named it plans every accepted feature still without a current plan. Use when asked to plan FEAT-001 in detail, prepare a story for implementation, generate agent prompts or task order, or record a task as in-progress, done or blocked. Do NOT use for writing criteria or tasks (use sw-craft) or writing code.
---

# sw-forge

The Dev role. Read an accepted story, write the detailed plan, stop. No code, no test run, no
write to a code root.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`03-plan/FEAT-NNN.plan.md`, `03-plan/prompts/FEAT-NNN/` (derived), the `Status:` and
`Evidence:` lines of its own tasks in `03-plan/FEAT-NNN.tasks.md`, and the story's condition
through `scripts/forge.py status`.

## Steps

1. No feature named → every row of `graph.py board --station plan --format json` not complete.
   Refuse a feature that is not accepted with a current approval, or whose tasks are stale
   against the story (`scripts/tasks.py --feat FEAT-NNN`).
2. `_shared/scripts/stack.py show`. Missing or unlocked → say so once; the plan still gets
   written and names each command it would need.
3. `graph.py context FEAT-NNN`; read only the listed files, the diagram and every local
   visual. Read code roots read-only to check a claim; never write there.
4. Plan from `assets/plan.md`: approach, constraints, ordering, risks, then **one detailed
   section per task** (`### TASK-NNN-k`) answering only for that task:
   exact files to create or change and where (`<code-root>/<path>`, or `new:<path>` for a
   folder to create), the change described concretely enough to apply without judgement,
   the test that proves it and the command that runs it (from the locked stack), the order
   against other tasks and what must exist first, and the condition under which a coder must
   stop and ask. A claim about code needs a path from `Touches`, else `UNKNOWN`.
5. Tasks as the BA wrote them are the contract: do not re-number, re-scope or re-layer. Set
   each task's `Status: planned` as its plan section is written, and keep one section per
   active task (`scripts/tasks.py --feat FEAT-NNN` reports the plan, too).
6. `_shared/scripts/finish.py` writes the prompts (`scripts/task_prompts.py`) for ready
   tasks; its output carries the stack check. Run `_shared/scripts/stack.py check --feat
   FEAT-NNN` directly only when you need the findings on their own.
7. The story's condition follows its tasks: `forge.py status` recomputes `in-development`
   while any task is `in-progress`, and `done` when every task is `done` **and** every
   acceptance criterion has evidence.

## Status loop

    scripts/forge.py status TASK-001-1 in-progress
    scripts/forge.py status TASK-001-1 done --evidence "make test → 42 passed, exit 0"
    scripts/forge.py status TASK-001-1 blocked --reason "BR-001 undefined for tiers above 3"

`planned` is set when the plan section exists. `done` needs evidence. A story never reaches
`done` while a task is open or an acceptance criterion has no evidence. Mark a whole story at
once with `scripts/forge.py plan --feat FEAT-NNN`.

## Stop when

Feature not accepted; tasks stale; an AC with no plan section; plan/story conflict; tasks break
the locked stack; a change request must be applied first.

## Finish

Run `_shared/scripts/finish.py --skill sw-forge --subject "<FEAT-NNN> plan" --cwd <project>`
(add `--item` per named item, `--until <station>` if the user set a limit). Act on
`handoff.mode`: `continue` → print `say`, apply `transitions`, load `../<next_skill>/SKILL.md`
now; `repair` → fix lint once, rerun with `--repaired`; `confirm` → ask once; `stop` → ask
what `waiting` needs; `done` → report the code roots it targeted, the plan and the prompts,
and say the code is written elsewhere from `03-plan/prompts/FEAT-NNN/_order.md`.

## Load only when

| Need | File |
| --- | --- |
| Task field rules, examples | references/task-format.md |
| Detailed plan sections, wording | references/plan-detail.md |
| Stack lock, changes, check | references/stack.md |
| Agent prompt layout | references/task-prompts.md |
| Several features | _shared/references/parallel-writers.md |
| A step above is unclear or a script errors | references/procedure.md |
