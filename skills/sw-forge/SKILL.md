---
name: sw-forge
description: Writes detailed implementation plans and task prompts from accepted stories and tasks. Use when planning FEAT-001, preparing implementation, generating task order or prompts, or recording task progress and evidence. With no feature named, plans all accepted features without a current plan. Do NOT use for stories or task definitions (use sw-craft), publishing (use sw-ship), or writing code.
---

# sw-forge

The Dev role. Read an accepted story, write the detailed plan, stop. No code, no test run, no
write to a code root.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`plans/FEAT-NNN/FEAT-NNN.plan.md`, `tasks/FEAT-NNN/prompts/` (derived), the `Status:` and
`Evidence:` lines of its own tasks in `tasks/FEAT-NNN/FEAT-NNN.tasks.md`, and the story's condition
through `scripts/forge.py status`.

## Steps

1. No feature named → every row of `graph.py board --station plan --format json` not complete.
   Refuse a feature that is not accepted with a current approval, or whose tasks are stale
   against the story (`scripts/tasks.py --feat FEAT-NNN`).
2. `_shared/scripts/stack.py show`. Missing or unlocked → say so once; the plan still gets
   written and names each command it would need.
3. `graph.py context FEAT-NNN`; read only the listed files, the diagram and every local
    visual. Read code roots read-only to check a claim; never write there.
   Existing root docs or plans not linked yet → use sw-craft's repository-context procedure,
   not an automatic import or replacement plan. Ask with evidence and options for missing
   decisions in any state; leave unanswered choices open and plan only independent work.
4. Plan from `assets/plan.md`: approach, constraints, ordering, risks, then **one detailed
   section per task** (`### TASK-NNN-k`) answering only for that task:
   exact files to create or change and where (`<code-root>/<path>`, or `new:<path>` only when
   that parent directory already exists under a registered code root; otherwise `UNKNOWN`),
   the change described concretely enough to apply without judgement,
   the test that proves it and the command that runs it (from the locked stack), the order
   against other tasks and what must exist first (tasks that touch the same path name each
   other in `Depends on`; `None` is not the default), and the condition under which a coder
   must stop and ask. A claim about code needs a path from `Touches`, else `UNKNOWN`.
   `scripts/tasks.py --mark-ready` refuses until this plan exists.
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

Run `_shared/scripts/finish.py --skill sw-forge --subject "<FEAT-NNN> plan" --cwd <project>`.
Follow `_shared/references/handoff.md` for item selection, limits and every `handoff.mode`.
`finish.py` also reports `newly_ready`: the items that became startable since the last build. Name them in the reply.
On `done`: Report the targeted code roots, plan and prompts. State that implementation runs elsewhere from `tasks/FEAT-NNN/prompts/_order.md`.

## Load only when

| Need | File |
| --- | --- |
| Task field rules, examples | references/task-format.md |
| Detailed plan sections, wording | references/plan-detail.md |
| Stack lock, changes, check | references/stack.md |
| Agent prompt layout | references/task-prompts.md |
| Several features | _shared/references/parallel-writers.md |
| A step above is unclear or a script errors | references/procedure.md |
