# Task format

File: 03-plan/FEAT-001.tasks.md. Front matter holds feat, spec_hash, status (draft or ready) and assets
(the visual references the tasks use).

Each task is a level-three heading followed by labelled lines:

    ### TASK-001-1 — [backend] Record an eligible refund request
    Traces to: AC-001-1, BR-001
    Touches: src/refunds/request.py
    Depends on: None
    Done when: Order R100 paid 50 USD on day 3 yields one pending request for 50 USD.
    Stop and ask if: the refund window is not defined in BR-001.

    ### TASK-001-2 — [frontend] Show the refund form with its error state
    Traces to: AC-001-2
    Visuals: ASSET-001, diagrams/FEAT-001.flow.svg
    Depends on: TASK-001-1
    Done when: A refund over the paid amount shows the error state drawn in ASSET-001.
    Stop and ask if: ASSET-001 does not show the state an AC needs.

Rules:

- Heading: `[layer]` prefix, then a verb-first title with one outcome. A parallel-safe task adds [P]
  at the end of the title.
- Layer: exactly one of backend, frontend, mobile, devops, data, qa, design, docs. A criterion
  that needs more than one layer becomes one task per layer, ordered with Depends on (API
  before the screen that calls it, pipeline before the deploy). Never put two layers in one task.
- Visuals: the ASSET IDs (and `diagrams/` paths) of the mockup, Figma link, screenshot or
  diagram the task builds from, copied from the story's UI/UX list. Required on frontend, mobile
  and design tasks when the story lists any visual; optional elsewhere (a backend task may cite
  a sequence diagram). Done when names the state or screen the visual shows. Omit the line when
  there is nothing to cite.
- Traces to: at least one AC. Add BR or NFR where the rule drives the task.
- Done when: copy the observable result of the AC with concrete values.
- Touches: relative paths only, embedded projects only; the graph checks existence.
- Depends on: task IDs or None.
- Stop and ask if: the condition under which the agent must stop rather than assume.
- Withdrawn tasks stay as ~~TASK-001-3~~ with a reason. Numbers are never reused.
- Every active AC needs at least one task.
