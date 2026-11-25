# sw-plan — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

0. No feature named (a bare `/sw-plan`, or "plan what is left"): take the whole plan backlog, not
   one item. Rebuild the graph if it is stale, then read
   `_shared/scripts/graph.py board --station plan --format json --cwd <project>`; the backlog is
   every row whose condition is not `complete` (no tasks file, stale tasks, or a failing check).
   Put the items already started first (a draft `03-plan/FEAT-NNN.tasks.md` exists), then the rest
   in the order of `start.py` ranking. Show one table (feature, condition, why) and run
   "Several features" below for all of them, one worker per feature; with a single item, plan it
   directly. A feature that is not accepted is listed as skipped with its reason, never planned.
   Naming a feature plans only that one.
1. Resolve scope before any write. Refuse a feature that is not accepted (status
   ready-to-publish, published or ready-for-dev); point to sw-review. Active approval must
   also be current, not just the status label: a fresh accept line or verified sign-off
   under `signoff: optional`, a verified sign-off only under `required`
   (_shared/references/governance.md).
2. Run the shared graph context query for the feature
   (_shared/references/query-cookbook.md) and read only the listed story, rules,
   diagrams, records and asset files. Read the diagram when one illustrates the
   feature. When the chip says no illustration, note that and leave the story as prose.
   Read the story's UI/UX Visuals list: open every local mockup, image or diagram file (a story's embedded diagram is the `.svg` under `diagrams/`) and
   carry each Figma or other link as a link (never fetch it). Copy the visuals' ASSET IDs into
   the tasks front matter `assets`.
3. Write the plan from assets/plan.md: approach, constraints, referenced rules,
   dependencies, evidence, open Dev questions. A claim about existing code needs a file
   path as evidence, otherwise write UNKNOWN. Use the code graph tool for symbols only
   when the project has one.
4. Write tasks from assets/tasks.md using references/task-format.md. Number tasks
   TASK-<feature number>-<n>; never reuse a number; keep withdrawn tasks as
   ~~TASK-001-3~~ lines. Split work by layer: every title starts with one `[layer]` prefix
   (backend, frontend, mobile, devops, data, qa, design, docs); a criterion that needs more
   than one layer becomes one task per layer, ordered with Depends on.
5. Every task has Traces to (at least one AC; add BR or NFR where the rule drives it), Done when (the observable check copied from
   the AC), Depends on and Stop and ask if. Add Touches only in an embedded project and
   only for paths that exist. When the story lists visuals, every frontend, mobile and design
   task has a `Visuals:` line naming the mockup or diagram it builds, and its Done when names
   the state or screen that visual shows. A state an AC needs that no visual shows is a
   question, not a guess.
6. Copy the story's Identity `Draft hash:` value into the tasks front matter as spec_hash. Run
   `scripts/check_tasks.py --feat FEAT-NNN` (add `--scope SCOPE` in a program); fix findings and
   rerun.
7. Only a passing check allows status ready (`check_tasks.py --feat FEAT-NNN --mark-ready`); ready
   records coverage, not human approval.
8. Maintenance: `_shared/scripts/graph.py build --cwd <project>`, then
   `_shared/scripts/sw_lint.py --root <project> --gate review` and `_shared/scripts/graph.py check`,
   then `_shared/scripts/data.py export tasks --as sw-plan`. Report failures as incomplete
   maintenance.

## Several features

Two or more accepted features of one scope that lack a current plan are planned in
parallel, one sub-agent per FEAT, as the default. A worker writes only its own
`03-plan/FEAT-NNN.plan.md` and `03-plan/FEAT-NNN.tasks.md`, runs steps 1 to 6 and check_tasks.py
for that feature, and returns the result. The lead guards the writes with
`_shared/scripts/parallel_guard.py` (allow `FEAT-NNN=03-plan/FEAT-NNN.*`), then runs step 8
(graph, lint, data export) once. Rules: _shared/references/parallel-writers.md. A worker
for a feature that fails step 1 writes nothing and reports why.

## After the batch

Report one line per feature: its station and condition, and the check result. Then run
`_shared/scripts/handoff.py next --done sw-plan` (`--item` when one was named) and act on it
(_shared/references/handoff.md). Planning is the last local station: for the planned features
the answer is `done`. In a whole-scope run the chain goes on to items still at earlier stations
(spec, then review) without a question under `flow: auto`. A failing check after the one repair
pass is a stop. Publication is entered on an explicit request, never offered as a next step.

## Consumer check

Dev: can each task start from its own text, with inputs, order and limits clear? QA: can
each Done when become a test with a concrete input and expected result? Record each "no"
as a question.

## Stop and ask

Stop on an unreviewed feature, an uncovered AC with no sensible task, or a plan/story
conflict. Questions follow `_shared/references/stop-and-ask.md`. Never invent business rules to
fill a gap.

## Gotchas

- A changed story makes tasks stale; the hash check reports it. Regenerate tasks; do not patch them.
- Status-only rollback blocks tasks by eligibility; only a real story-content change makes spec_hash stale.
- Parallel workers write only their own plan and tasks files; the lead refreshes graph, lint and data once.
- Tasks are never published to Jira.
- Ready means covered, not approved.
- Touches paths are declared and existence-checked, never guessed.
- Every task has one layer prefix; frontend, mobile and design tasks cite the story's visuals.
