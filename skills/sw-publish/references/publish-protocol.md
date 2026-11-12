# Publish protocol

Sequence from accepted draft to confirmed, executed change. Every remote write binds to a
fresh confirmation of the exact plan shown.

## Preconditions (all must hold)

- Draft front matter `status` is exactly `ready-to-publish` (shown as accepted).
- Approval is current: a fresh accept line or sign-off for the current draft hash when
  `signoff: optional`; a sign-off with an HTTPS evidence URL and that hash when `required`
  (`sha256:` short form). A plan or tasks are not a precondition.
- The publish lint report exists and shows `0 blocking error(s)`. Produce it with
  `_shared/scripts/sw_lint.py --gate publish`.
- Manifest `publish.transitions` is false. Transitions stay off unless the manifest grants
  them and a separate human confirms.

Any failure stops the plan. Fix it through the owning skill; never weaken a gate.

## Identity

The registry `Jira key` is authoritative. When absent, labels and the entity property only
name candidates: more than one candidate stops the run, and a property naming another
feature stops it. No candidate reads as `NEW`. Re-read the remote update timestamp
immediately before an edit.

## Confirmation

The plan renders `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`. The user confirms the exact
plan in the current session (a plain "yes" to the dry-run just shown; the agent then passes
the token); a stored value never authorizes a write. The short hash binds the
confirmed plan, so any later change to draft or plan invalidates it. Never retry an
ambiguous create: reconcile identity and stop.

## Execution

The write capability runs the confirmed plan one operation at a time, checking each is
still part of the confirmed hash. Local index rows (registry Jira key, RTM Jira column,
card status) update only after every remote operation succeeds.
