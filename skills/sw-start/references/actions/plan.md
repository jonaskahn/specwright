# Plan action

Turns a reviewed feature into an implementation plan and traceable agent tasks, each
task tracing to acceptance criteria, rules and optional code paths, with a coverage
check that flags stale tasks. This is an explicit action inside Specify.

## Steps

1. Resolve scope and read the reviewed story and any code-path evidence. Do not invent
   dependencies from inference alone.
2. Fill assets/plan.md and assets/tasks.md. Keep task IDs stable; withdrawn IDs remain
   tombstones.
3. Render dependency or architecture diagrams only when supported by evidence and
   useful to the requested plan.
4. Run scripts/check_tasks.py. Exit 0 means every criterion is covered; fix findings
   through the plan before hand-off.
5. Refresh the graph after saving the plan and any collected assets.

## Boundaries

- Planning does not write to Jira; tasks stay Markdown.
- Coverage is not human approval.
