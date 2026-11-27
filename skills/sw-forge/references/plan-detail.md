# Detailed plan sections

`03-plan/FEAT-NNN.plan.md` keeps the six plan sections every feature has, then adds one
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
    Order: first; TASK-001-2 and TASK-001-3 need this type.
    Stop and ask if: BR-001 is undefined for an order with two partial payments.

Rules:

- One section per active task, in dependency order; no section for a withdrawn task.
- `Files:` names every file created or changed and the registered code root it lives in. A file
  outside every root is `UNKNOWN` until the user registers a root; never invent a path.
- `Change:` describes the behaviour and the shape (signature, type, field), not a diff. It cites
  the AC or BR it satisfies.
- `Test:` is the test that proves `Done when`, with the concrete values of the criterion.
- `Command:` comes from `stack.py show` for the task's layer; no layer, no command, and the
  task says why.
- `Order:` says what must exist first and which tasks depend on this one.
- `Stop and ask if:` is the single condition under which guessing is worse than stopping.

## Plan front matter

```yaml
feat: FEAT-NNN
type: plan
status: draft
plan_hash: <hash of the story the plan was written from>
```

The six sections in `assets/plan.md` stay: Approach, Visual references, Constraints,
Dependencies, Evidence from the codebase and Open Dev questions come before the per-task
sections. `scripts/tasks.py --feat FEAT-NNN` refuses a plan missing a section for an active
task and flags a section for a task that is gone.
