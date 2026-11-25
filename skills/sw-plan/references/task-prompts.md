# Agent task prompts

`scripts/task_prompts.py --feat FEAT-NNN` (finish.py runs it for ready tasks) writes
`03-plan/prompts/FEAT-NNN/TASK-NNN-k.md` and `_order.md` (dependency order).

Each prompt is self-contained, in this order: Goal · Done when · Acceptance criteria (verbatim)
· Rules (traced BR/NFR lines) · Stack (layer line, lock hash, forbidden, needs-approval,
conventions) · Inputs (Depends on, Touches, Visuals) · Rules of engagement (scope, stack only,
test command, stop conditions, report format).

- Derived files: never edit; change the story or tasks, then regenerate. Withdrawn tasks'
  prompts are removed on regeneration.
- Refused when tasks are not `ready` or are stale against the story (`--draft` overrides for
  preview; the prompt then says "DRAFT: do not start").
- Hand `_order.md` and the prompt files to the implementing agent, one task per session.
