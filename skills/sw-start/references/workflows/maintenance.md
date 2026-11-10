# Maintenance workflow

Maintenance supports every stage with status, knowledge, trace, lint and the
completion procedure. It is not a separately installed skill.

## Steps

1. Status: run scripts/status.py --cwd <project> for a read-only position report.
2. Knowledge: run scripts/graph.py map to read the map, build after saved plans and
   other relevant changes, then check. Read the graph through its queries instead of
   opening every file.
3. Trace: run scripts/trace.py rebuild or set only through the owning operation.
4. Lint: run scripts/sw_lint.py with the applicable gate before hand-off.
5. Completion: apply references/shared/completion.md after the requested action.

## Boundaries

- Status and knowledge queries are read-only.
- The graph is derived; if it disagrees with a file, the file wins.
- Trace column ownership is enforced, not advisory.
- A failing lint gate is reported, never silently waived.
