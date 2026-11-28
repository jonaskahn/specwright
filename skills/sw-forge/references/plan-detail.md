# Detailed plan sections

`plans/FEAT-NNN/FEAT-NNN.plan.md` keeps the six plan sections every feature has, then adds one
level-three section per active task. The file is the Dev's contract: a coder applies it without
asking what was meant.

## Per-task section

    ### TASK-001-1 — [backend] Record an eligible refund request

    Files: refunds/service.py (new) · refunds/test_service.py (new root: shop-api)
    Change: `RefundService.request(order, now)` reads BR-001's window, refuses after 14 days
    with `RefundWindowClosed`, and returns a `RefundRequest(amount, status="pending")` for the
    paid amount when the order was delivered within the window.
    Test: refunds/test_service.py::test_day_3_full_amount — order R100 paid 500 USD on day 3
    yields one pending request for 500 USD.
    Command: `mvn -q -Dtest=RefundServiceTest test` (from stack: backend)
    DoD: request refused after day 14; pending request stored; `make check` passes.
    Accepts: AC-001-1 (day-3 request is accepted for the full amount)
    Coverage: line 85% and branch 75% on refunds/service.py; every BR-001 branch has a test.
    Order: first; TASK-001-2 and TASK-001-3 need this type.
    Stop and ask if: BR-001 is undefined for an order with two partial payments.

Rules:

- One section per active task, in dependency order; no section for a withdrawn task.
- `Files:` names every file created or changed and the registered code root it lives in. A file
  marked `(new)` follows the task `Touches` rule: `new:<path>` only when the parent directory
  exists under a registered root. A file outside every root is `UNKNOWN` until the user
  registers a root; never invent a path.
- `Change:` describes the behaviour and the shape (signature, type, field), not a diff. It cites
  the AC or BR it satisfies.
- `Test:` is the test that proves `Done when`, with the concrete values of the criterion.
- `Command:` comes from `stack.py show` for the task's layer; no layer, no command, and the
  task says why.
- `DoD:` lists the observable conditions that make the task done; `Accepts:` names the AC IDs
  the task proves; `Coverage:` states the metric and target the tests must reach. A project may
  set one default in `project.yaml` (`coverage: {line: 80, branch: 70}`); a plan restates it per task.
- `Order:` says what must exist first and which tasks depend on this one.
- `Stop and ask if:` is the single condition under which guessing is worse than stopping.

## Plan front matter

```yaml
feat: FEAT-NNN
type: plan
status: draft
tasks: [TASK-001-1, TASK-001-2]
plan_hash: <hash of the story the plan was written from>
```

The six sections in `assets/plan.md` stay: Approach, Visual references, Constraints,
Dependencies, Evidence from the codebase and Open Dev questions come before the per-task
sections. `scripts/tasks.py --feat FEAT-NNN` refuses a plan missing a section for an active
task and flags a section for a task that is gone.
