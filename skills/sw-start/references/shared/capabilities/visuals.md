# Visuals capability

Produces offline diagrams and illustration templates when a picture is justified, and
checks existing visuals before calling them current. This is the shared replacement
for the old sw-draw skill.

## Need check

Read references/domain/illustration-need.md before drawing. A current illustration is
a no-op. Fewer than five items and one actor means use a paragraph; do not invent
actors to bypass the gate. No diagram creates policy or approval.

## Workflow triggers

- Shape: render only when a process or context picture resolves a concrete ambiguity.
- Specify: render for complex behavior, state transitions, meaningful UI
  relationships or stale referenced pictures.
- Plan: render dependencies or architecture only when supported by evidence and useful.
- Review: detect missing, stale or invalid visuals and report findings; repair within
  scope before final hash and approval.
- Publish: validate referenced assets and visuals before the final dry-run.

## Rendering

Select a type with references/domain/type-picker.md and the matching
references/domain/type-*.md entry. Run scripts/render_diagram.py with absolute JSON
and approved output paths. Prefer .svg for portable embedding, .html for the exact
data table and local navigation. Run scripts/check_borders.py and
scripts/check_offline.py on every artifact. Escape external text before putting it in
HTML. Generated diagrams are offline with full borders, outlines, tints or shadows.
