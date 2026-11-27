# sw-forge — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

0. No feature named (a bare `/sw-forge`, or "plan what is left"): take the whole plan backlog,
   not one item. Rebuild the graph if it is stale, then read
   `_shared/scripts/graph.py board --station plan --format json --cwd <project>`; the backlog is
   every row whose condition is not `complete`. Put the items already started first (a plan file
   with task sections exists), then the rest in `start.py` ranking order. Show one table
   (feature, condition, why) and run "Several features" for all of them, one worker per feature.
   A feature that is not accepted is listed as skipped with its reason, never planned.
1. Resolve scope before any write. Refuse a feature that is not accepted (status
   ready-to-publish, published or ready-for-dev); point to sw-craft. The approval must also be
   current (`_shared/references/governance.md`), and the tasks must not be stale: run
   `scripts/tasks.py --feat FEAT-NNN` and stop on its findings.
2. Read the graph context for the feature (`_shared/references/query-cookbook.md`) and only the
   listed story, rules, diagrams, records and asset files. Open every local mockup, image or
   diagram; carry a Figma or other link as a link, never fetch it.
3. Check the code a task touches, read-only: does the path in `Touches:` exist, and does the
   change fit the code that is there? Never write inside a code root. A claim about code needs
   a file path as evidence, otherwise UNKNOWN.
4. Fill `assets/plan.md`: approach, visual references, constraints, dependencies, evidence and
   open Dev questions, then one per-task section in dependency order
   (`references/plan-detail.md`). Set `Status: planned` on each task as its section is written
   (`scripts/forge.py plan TASK-001-1`, or `scripts/forge.py plan --feat FEAT-NNN`), and keep
   every section in dependency order.
5. Run the BA contract check `scripts/tasks.py --feat FEAT-NNN`: it confirms coverage and
   that the plan has one section per active task, the six plan sections and a
   `Files:`/`Change:`/`Test:`/`DoD:`/`Accepts:`/`Coverage:` line in each and a `tasks:` front-matter list of every active task. Fix findings and rerun.
6. Copy nothing in the tasks file except the `Status:` and `Evidence:` lines; the BA's text is
   the contract. Withdraw a task only with the user's word, as a `~~TASK-001-3~~` tombstone.
7. `_shared/scripts/finish.py --skill sw-forge` regenerates `03-plan/prompts/FEAT-NNN/` from the
   ready tasks (`references/task-prompts.md`) and reports the stack check.
8. Status: `scripts/forge.py status <TASK> <state>` rewrites the task line and the story's
   condition together (`in-development` while a task is `in-progress`, `done` only when every
   task is `done` and every AC has evidence). `done` without `--evidence` is refused.

## Several features

Two or more accepted features of one scope that lack a current plan are planned in
parallel, one sub-agent per FEAT, as the default. A worker writes only its own
`03-plan/FEAT-NNN.plan.md` and its task `Status:` lines, runs steps 2 to 5 and
`tasks.py` for that feature, and returns the result. The lead guards the writes with
`_shared/scripts/parallel_guard.py` (allow `FEAT-NNN=03-plan/FEAT-NNN.*`), then runs step 7
once. Rules: _shared/references/parallel-writers.md. A worker for a feature that fails step 1
writes nothing and reports why.

## After the batch

Report one line per feature: its station and condition, the tasks it marked planned and the
code roots the plan targets. Then run `_shared/scripts/handoff.py next --done sw-forge` and act
on it (`_shared/references/handoff.md`). Planning is the last local station: the answer is
`done`, and the deliverables are the plan, the prompts and the statuses, not code.

## Consumer check

Dev: can each task start from its section alone, with the files, the change, the test, the
command and the order clear? QA: can `Test:` become a test with a concrete input and expected
result? Record each "no" as an open Dev question rather than a guess.

## Stop and ask

Stop on an unreviewed or stale feature, an AC with no plan section, or a plan/story conflict.
Questions follow `_shared/references/stop-and-ask.md`. Never invent a business rule or a file
path to fill a gap.

## Gotchas

- A changed story makes tasks stale; the hash check reports it. Ask sw-craft to regenerate.
- A task without `Status:` reads as not-started; that is compatible, not an error.
- The plan never writes code and never runs the test command; it states it.
- Ready means covered, not approved; done means proven, and needs `Evidence:`.
- A task in `new:` mode names a folder to create; the coder creates it, the plan does not.
