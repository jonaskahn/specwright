# Task format (the BA contract, with status)

File: `tasks/FEAT-NNN/FEAT-NNN.tasks.md`. Front matter holds `feat`, `spec_hash`, `status` (draft or
ready) and `assets`.

Each task is a level-three heading followed by labelled lines:

    ### TASK-001-1 — [backend] Record an eligible refund request
    Traces to: AC-001-1, BR-001
    Stack: java 21 · spring-boot 3.3 · maven · test: mvn test
    Touches: shop-api/src/refunds/service.py
    Depends on: None
    Done when: Order R100 paid 500 USD on day 3 yields one pending request for 500 USD.
    Stop and ask if: the refund window is not defined in BR-001.
    Status: planned

Rules (write for agents: `_shared/references/agent-style.md`):

- Heading: one `[layer]` prefix, then a verb-first title with one outcome. sw-craft writes the
title and the lines below it; sw-forge never re-numbers, re-scopes or re-layers a task.
- `Status:` one of `not-started`, `planned`, `in-progress`, `done`, `blocked`. A task without
  the line reads as `not-started`, so older files still parse. On a new task it is
  `not-started`; from then on sw-forge owns it.
- `Evidence:` and `Blocked because:` are not the BA's to write: sw-forge records them with
  `forge.py status` when the code elsewhere proves the task.
- `Touches:` a path that resolves against a registered code root (`shop-api/src/...`), or
  `new:<path>` for a folder the work creates. A path outside every root is a finding.
- Layer: exactly one of backend, frontend, mobile, devops, data, qa, design, docs (in
  `schema.TASK_LAYERS`). A criterion that needs more than one layer is one task per layer.
- Visuals: the ASSET IDs and `diagrams/` paths the task builds from; required on frontend,
  mobile and design tasks when the story lists a visual.
- `Traces to:` at least one AC, plus BR or NFR where the rule drives the task.
- `Done when:` the AC's observable result with concrete values.
- `Depends on:` task IDs or None; a task is ready only when each one is done. A feature or epic states the same links as `depends_on: [FEAT-001]` in its front matter. `Stop and ask if:` the condition to stop rather than assume.
- Withdrawn tasks stay as `~~TASK-001-3~~` with a reason; numbers are never reused.
- Every active AC needs at least one task; sw-forge checks coverage and the plan.
