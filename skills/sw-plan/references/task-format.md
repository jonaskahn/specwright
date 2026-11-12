# Task format

File: 03-plan/FEAT-001.tasks.md. Front matter holds feat, spec_hash, status (draft or ready) and assets.

Each task is a level-three heading followed by labelled lines:

    ### TASK-001-1 — Record an eligible refund request
    Traces to: AC-001-1, BR-001
    Touches: src/refunds/request.py
    Depends on: None
    Done when: Order R100 paid 50 USD on day 3 yields one pending request for 50 USD.
    Stop and ask if: the refund window is not defined in BR-001.

Rules:

- Heading: verb first, one outcome. A parallel-safe task adds [P] at the end of the title.
- Traces to: at least one AC. Add BR or NFR where the rule drives the task.
- Done when: copy the observable result of the AC with concrete values.
- Touches: relative paths only, embedded projects only; the graph checks existence.
- Depends on: task IDs or None.
- Stop and ask if: the condition under which the agent must stop rather than assume.
- Withdrawn tasks stay as ~~TASK-001-3~~ with a reason. Numbers are never reused.
- Every active AC needs at least one task.
