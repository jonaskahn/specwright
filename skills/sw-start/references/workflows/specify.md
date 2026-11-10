# Specify workflow

Specify writes or amends feature story drafts and compact cards with concrete
Given/When/Then criteria, worked business rules, measurable NFRs and Dev/QA checks.
Implementation planning is an explicit action inside this workflow.

## Steps

1. Resolve scope before writing: explicit scope, qualified ID, project path, flat
   manifest, otherwise ask. Determine new, resume or amendment from files, not memory.
   An unaccepted idea goes to Shape; do not reserve a FEAT before PO acceptance.
2. For published content, obtain the latest Jira snapshot through normal ingestion
   and start from that immutable baseline, not the stale local draft. Require a real
   CR-NNN record; if absent, stop the amendment. Never overwrite the snapshot.
3. For a new accepted feature, run scripts/new_story.py with --scope-root, --scope
   and --summary. It reserves the next ID and refuses reuse. Resume existing drafts
   by editing, not by reallocating.
4. Fill all twelve sections, retaining headings and order. Use references/domain/ac-writing.md,
   references/domain/ears.md, references/domain/business-rules.md and
   references/domain/nfr-defaults.md. Write at least two concrete criteria; cover the
   happy path, each business-rule branch, boundaries and enumerated error outcomes.
   Keep AC IDs stable; retain withdrawn IDs as tombstones.
5. For complex behavior, state transitions, meaningful UI relationships or stale
   referenced pictures, evaluate the illustration need with
   references/domain/illustration-need.md and use the shared visuals capability when
   justified. Do not render a picture for every spec.
6. For a task breakdown, read references/actions/plan.md and run
   scripts/check_tasks.py. Planning runs only when the user asks for it or it is in
   the agreed scope.
7. Refresh the compact card with scripts/card_gen.py after body edits; compute the
   content hash inside the Identity section. Run scripts/sw_lint.py before hand-off.

## Boundaries

- Request RTM updates only through the trace capability for owned columns.
- Never create rows or edit columns owned by another operation.
- Do not store credentials or unnecessary personal data.
