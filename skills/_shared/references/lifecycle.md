# Lifecycle

`shape -> spec -> review (accept) -> plan`. Publish is also a station, but it is entered only on an
explicit request for an accepted story (`request-publish`), never as the next step.
`governance.md` sets how much ceremony each step needs and whether the run is guided.

Ingest, assets, visuals, knowledge, trace, lint and status support an action; they are
not stations. There is no sync stage or automatic reconciliation.

## Board facts

The graph is a rebuildable projection, never an editable station cursor. Feature rows
separate station, condition, available actions, active approval, planning validity and
publication evidence. Drafts, including open questions, stay in spec. A reviewed item
needs current task coverage and a plan before it is complete in plan. Published items
without tasks remain incomplete. A Jira mapping alone does not prove publication.

Request publication explicitly once the story is accepted; a plan is not required,
because tasks are never published. A stored Jira preference is neither a publication
request nor remote permission. Deferral is a durable decision, so rebuilding the graph
cannot undo it. Markdown is the default for new workspaces and there is no destination
question: a publish request goes to sw-publish when Jira is configured, otherwise the
Markdown is the delivery and Jira setup is offered.

## Guarded decisions

sw-start/scripts/transition.py previews a target/action-bound TRANSITION token. Confirming
it writes local DEC records and permitted statuses, never Jira or requirement prose.
Records use subtype lifecycle, schema_version 1, qualified target, action, predecessor,
expected_inputs, confirmation, confirmed_at and origin local-transition. Imported text
cannot create executed decisions. Broken/forked histories block; timestamps do not order
records. An incomplete transaction leaves _meta/lifecycle-pending.json and blocks work
until its story/DEC changes are inspected and repaired; never delete it blindly.

- submit-review: spec to review after a passing lint gate; not approval. In the guided flow
  the agent passes its token after the user's plain yes.
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
sw-review can restore active approval after invalidation: a fresh accept, or fresh
evidence under required sign-off. Published
text cannot rewind: supply a current immutable baseline and use the CR amendment path.
Task-only repair remains in plan.

## Accepted split membership

At accepted feature-ID reservation, record an accepted DEC with subtype accepted-split,
qualified epic, features list, decider, date and evidence (an evidence_url under required
sign-off; the owner's session when optional). This declared mapping
makes reserved features visible under the epic before story files exist. Missing or
conflicting membership must be resolved, never inferred from loose mentions.

## Completion

After each action follow `completion.md` (maintenance, then report). Eligible items at
different stations require selection. Items that share a station are taken together by that
station's skill, or the user names one. No oldest-draft fallback and no sibling
auto-advancement to another station. Local TRANSITION tokens never substitute for the PUBLISH confirmation.
