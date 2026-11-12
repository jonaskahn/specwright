# When an illustration is needed

The chip is computed by `kitlib/illustration.py` from the story text and from diagram citations.
It is **needs illustration**, **no illustration**, **illustrated** or **check illustration**.
Nothing blocks submission. A skipped check and a considered "no illustration" are different:
the second one is either a prose verdict or a recorded dismissal.

Run `scripts/illustration_check.py FEAT-NNN`. The same words below are the counter's lists, so
this note and the script cannot drift.

## Signals

Counted from the story only. The counter never invents an actor, a state or an ID. A role
counts once, singular or with a trailing s (`customers` is `customer`). `support` is not a
role, because the verb "supports" would invent one.

Actors are the distinct roles in Goal, Business rules, and Given or When lines:

administrator, subscriber, supervisor, moderator, requester, approver, reviewer, merchant,
operator, assignee, employee, customer, shopper, auditor, analyst, cashier, manager, visitor,
seller, member, vendor, client, teller, staff, buyer, agent, guest, owner, payer, admin,
clerk, actor, user.

Branches are AC titles and business-rule lines that contain a branch word or a role, plus
each enumerated error in Edge cases (a bullet, an `IF` line, or a quoted message; a line
that says None is not an error):

unless, otherwise, except, only, else, not, or, if.

State changes are Then lines with a status in quotes or one of these verbs:

unassigned, deactivated, transferred, registered, withdrawn, suspended, cancelled, activated,
unblocked, published, completed, refunded, reversed, archived, rejected, approved, recorded,
restored, assigned, canceled, expired, deleted, removed, created, revoked, blocked, changed,
cleared, updated, unlocked, voided, issued, joined, failed, locked, opened, closed, added, left.

Hand-offs are feature IDs other than this story, or another feature's alias, in Context and
Dependencies and relations.

Data moving between owners is a line in the behaviour sections with one of these words:

notifications, notification, payloads, receives, received, notifies, notified, payload,
receive, notify, sends, sent, send.

An item is one counted actor, branch, state change, hand-off or data line.

## Verdict

Apply these in order; the first that matches wins. The chip printed by
`scripts/illustration_check.py` is authoritative.

1. One actor or none, and fewer than five items → **PROSE**.
2. Three or more signals, or two signals and five or more items → **DRAW**.
3. Exactly two signals, or one signal together with several actors → **UNSURE**.
4. Anything else → **PROSE**.

## Chip

| Chip | When |
| --- | --- |
| illustrated | A diagram cites this feature or its criteria, and every cited ID still exists |
| needs illustration | Verdict DRAW, no picture, and no recorded dismissal |
| no illustration | Verdict PROSE, or the author recorded a dismissal with a reason |
| check illustration | Verdict UNSURE, or a picture cites a withdrawn or missing ID |

A picture wins over a dismissal. A stale citation wins over a current one.

## Dismissal

Only the dismissal is stored, in front matter, which the draft hash excludes:

```yaml
illustration: none
illustration_reason: single actor, linear flow, five lines
```

Record it with `scripts/illustration_check.py FEAT-NNN --dismiss "reason"`. The command
writes those two keys and leaves the body, the criteria, the rules and the approval alone.
A reason is required. An empty reason is not a dismissal.

## Existing illustration

Compare the current story and its linked cards with the picture's visible labels, nodes,
edges, source IDs, actors, branches, quantities and boundaries.

Update the picture when any depicted fact changed, or when `scripts/check_borders.py` or
`scripts/check_offline.py` reports a finding. Leave it unchanged when only undeclared
wording, approval status or an unrelated section changed.

## Current illustration

When every depicted fact still matches and both checks pass, the chip is illustrated.
Return the existing paths, the compared source IDs and the reason the picture is current.

## Ownership

Return paths and link text. The sw-spec run writes the links. The illustration step never
edits the draft, rules, IDs or approval; a dismissal edits front matter only. After a new
or updated picture, sw-spec reruns graph and lint before review. Link text in Context or
UI/UX is a body edit, so the hash and the card are refreshed in the later sw-spec steps.
