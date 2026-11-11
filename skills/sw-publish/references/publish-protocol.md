# Publish protocol

Sequence from ready draft to confirmed, executed change. Every remote write binds to a
fresh typed confirmation.

## Preconditions (all must hold)

- Draft front matter `status` is exactly `ready-to-publish`.
- At least one sign-off carries an HTTPS evidence URL and the current draft hash
  (`sha256:` short form). A URL without the matching hash is stale.
- The publish lint report exists and shows `0 blocking error(s)`. Produce it with
  `../_shared/scripts/sw_lint.py --gate publish`.
- Manifest `publish.transitions` is false. Transitions stay off unless the manifest grants
  them and a separate human confirms.

Any failure stops the plan. Fix it through the owning skill; never weaken a gate.

## Identity

The registry `Jira key` is authoritative. When absent, labels and the entity property only
name candidates: more than one candidate stops the run, and a property naming another
feature stops it. No candidate reads as `NEW`. Re-read the remote update timestamp
immediately before an edit.

## Confirmation

The plan renders `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`. The user types it in the
current session; a stored value never authorizes a write. The short hash binds the
confirmed plan, so any later change to draft or plan invalidates it. Never retry an
ambiguous create: reconcile identity and stop.

## Execution

The write capability runs the confirmed plan one operation at a time, checking each is
still part of the confirmed hash. Local index rows (registry Jira key, RTM Jira column,
card status) update only after every remote operation succeeds.
