# Lifecycle

`Prepare -> Shape -> Spec -> Review -> Plan -> optional Publish`

Seven public skills remain. Ingest, assets, visuals, knowledge, trace, lint and status
support the requested action without becoming extra progress stations. No sync stage
or automatic reconciliation exists.

## Board facts

The graph is a rebuildable projection, never an editable station cursor. Feature rows
separate station, condition, available actions, active approval, planning validity and
publication evidence. Drafts, including open questions, stay in spec. A reviewed item
needs current task coverage and a plan before it is complete in plan. Published items
without tasks remain incomplete. A Jira mapping alone does not prove publication.

Request publication explicitly only after planning passes. A stored Jira preference is
neither a publication request nor remote permission. Deferral is a durable decision,
so rebuilding the graph cannot undo it. Markdown is new workspaces' default; existing
settings remain unchanged. Explicit ambiguous publish requests still ask destination.

## Guarded decisions

sw-start/scripts/transition.py previews a target/action-bound TRANSITION token. Confirming
it writes local DEC records and permitted statuses, never Jira or requirement prose.
Records use subtype lifecycle, schema_version 1, qualified target, action, predecessor,
expected_inputs, confirmation, confirmed_at and origin local-transition. Imported text
cannot create executed decisions. Broken/forked histories block; timestamps do not order
records. An incomplete transaction leaves _meta/lifecycle-pending.json and blocks work
until its story/DEC changes are inspected and repaired; never delete it blindly.

- submit-review: spec to review after a passing lint gate; not approval.
- return-spec: review/plan/publish to spec; preserve files and invalidate active approval.
- return-review: plan to review, including unstarted plan; old approval remains history.
- reopen-shape: spec to shape for this feature slice only; siblings stay unchanged.
- accept-slice: shape to spec after explicit acceptance of the reopened slice.
- request-publish / defer-publish: enter or leave publication without erasing preferences.
- set-destination: persist the named item's preference; never permits a remote write.

Step-back maps publish to plan, review to spec, spec to shape, and plan to spec; an
unstarted plan (no tasks) returns to review instead. Reset uses the same guards, never
promotes forward, withdraws an ID, deletes an artifact or bypasses approval.

Metadata-only rollback preserves the story hash. Tasks are blocked by lifecycle state,
not falsely content-stale. A real requirement change makes spec_hash stale. Only
sw-review can restore active approval with fresh evidence after invalidation. Published
text cannot rewind: supply a current immutable baseline and use the CR amendment path.
Task-only repair remains in plan.

## Accepted split membership

At accepted feature-ID reservation, record an accepted DEC with subtype accepted-split,
qualified epic, features list, role/person/date and evidence_url. This declared mapping
makes reserved features visible under the epic before story files exist. Missing or
conflicting membership must be resolved, never inferred from loose mentions.

## Completion

Finish the requested action, perform bounded required maintenance, then report the
item's station and condition. More than one eligible item requires selection, even
when all share a station. No oldest-draft fallback and no sibling auto-advancement.
Only sw-publish may write remotely after the clean gate, three-way dry-run and fresh
exact-plan PUBLISH confirmation; local TRANSITION tokens cannot substitute for it.
