---
name: sw-plan
description: Turns accepted features into an implementation plan, layered tasks bound to the locked technology stack, and one self-contained prompt per task for an implementing agent (Claude Code or similar), with coverage and stack checks. With no feature named it plans every accepted feature still without a current plan. Use when asked to plan FEAT-001, break a story into tasks, lock or check the tech stack for tasks, prepare work or prompts for an AI agent or developer, or check that every AC has a task. Do NOT use for unreviewed ideas (use sw-shape), writing criteria (use sw-spec) or pushing tasks to Jira (not supported; tasks stay Markdown).
---

# sw-plan

Turn accepted features into a plan, layered tasks and one prompt per task for an implementing
agent, all bound to the locked stack.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`03-plan/FEAT-NNN.plan.md`, `03-plan/FEAT-NNN.tasks.md`, `03-plan/prompts/FEAT-NNN/` (derived).

## Steps

1. No feature named → every row of `graph.py board --station plan --format json` not complete.
   Refuse a feature that is not accepted with a current approval.
2. `_shared/scripts/stack.py show`. Missing or unlocked → say so once; tasks still get written.
3. `graph.py context FEAT-NNN`; read only the listed files, the diagram and every local visual.
4. Plan from `assets/plan.md`: approach, constraints, rules, dependencies, evidence. A claim about
   code needs a path, else `UNKNOWN`.
5. Tasks from `assets/tasks.md`: `TASK-<n>-<k>`, one `[layer]` prefix, one outcome. Fields:
   Traces to (≥ 1 AC), Stack (code layers; value from `stack.py show`), Visuals (UI tasks when the
   story has visuals), Depends on, Touches (existing paths, embedded only), Done when (the AC's
   observable result), Stop and ask if.
6. Copy the story's `Draft hash` to `spec_hash`. `scripts/check_tasks.py --feat FEAT-NNN`; fix;
   then `--mark-ready`.
7. Several features → one worker per FEAT; lead runs finish once (`_shared/references/parallel-writers.md`).

`finish.py` runs the stack check and writes the prompts (`scripts/task_prompts.py`) for ready tasks.

## Stop when

Feature not accepted; an AC with no sensible task; plan/story conflict; tasks break the locked
stack (finish reports it).

## Finish

Run `_shared/scripts/finish.py --skill sw-plan --subject "<FEAT-NNN> plan and tasks" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Task field rules, examples | references/task-format.md |
| Stack lock, changes, check | references/stack.md |
| Agent prompt layout | references/task-prompts.md |
| Several features | _shared/references/parallel-writers.md |
| A step above is unclear or a script errors | references/procedure.md |
