# Visuals capability

Produces offline diagrams and illustration templates when a picture is justified, and
checks existing visuals before calling them current. It is bundled inside `sw-spec`.

## Need check

Read sw-spec's references/illustration-need.md before drawing. A current illustration is
a no-op. Fewer than five items and one actor means use a paragraph; do not invent
actors to bypass the gate. No diagram creates policy or approval.

## Workflow triggers

- Shape: render only when a process or context picture resolves a concrete ambiguity.
- Specify: run illustration_check.py and act on the chip. Render and embed when the chip says a
  picture is needed: complex behavior, state transitions, meaningful UI relationships
  or a stale picture.
- Plan: render dependencies or architecture only when supported by evidence and useful.
  Read a diagram when one exists; note no illustration when the chip says so.
- Review: report the illustration chip. A warning does not block approval. Repair a
  stale picture within scope before the final hash.
- Publish: validate referenced assets and visuals before the final dry-run.

## Rendering

Select a type with sw-spec's references/type-picker.md and the matching
references/type-*.md entry. Run sw-spec's scripts/render_diagram.py with absolute JSON
and approved output paths. Draw .svg by default and embed it in the story with
sw-spec's scripts/embed_diagram.py; .html is an optional companion for the exact data
table and local navigation, never the only file. Run sw-spec's scripts/check_borders.py and
scripts/check_offline.py on every artifact. Escape external text before putting it in
HTML. Generated diagrams are offline with full borders, outlines, tints or shadows.
