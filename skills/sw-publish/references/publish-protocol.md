# publish protocol

Own the sequence from a ready draft to a confirmed, executed change. Only sw-publish
writes to Jira or Confluence; every remote write is bound to a fresh, typed confirmation.

## Preconditions (all must hold before a plan is valid)

- The draft front matter status is exactly `ready-to-publish`.
- At least one sign-off carries an HTTPS evidence URL **and** the current draft hash
  (`sha256:` short form). A URL without the matching hash is stale.
- The publish lint report exists and contains `0 blocking error(s)`. Run the publish
  gate (`scripts/sw_lint.py --gate publish`) to produce it.
- The manifest `publish.transitions` is false. Workflow transitions stay off unless the
  manifest grants them and a separate human confirms.

Any failure stops the plan; fix it through the owning skill, never by weakening a gate.

## Identity

The registry `Jira key` is authoritative. When absent, labels and the entity property
name candidates only: more than one candidate stops the run, and a property naming a
different feature stops it. No candidate reads as `NEW`. Re-read the remote update
timestamp immediately before an edit.

## Confirmation

The plan renders a token of the form `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`. The user
must type that token in the current session; a stored value never authorizes a write.
The short hash binds the confirmed plan, so any later change to the draft or plan
invalidates it. An ambiguous create is never retried — reconcile identity and stop.

## Execution

The write capability executes the confirmed plan operation by operation, checking each
operation is still part of the confirmed hash. Local index rows (registry Jira key, RTM
Jira column, card status) update only after every remote operation succeeds.
