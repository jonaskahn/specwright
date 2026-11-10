# approval evidence

sw-sync does not decide approval; it detects when an existing sign-off went stale.

## Staleness check

A sign-off is stale when its recorded `sha256:<12>` no longer matches the current draft
hash. A drift class of `content-edited` on a published requirement is the common cause.

## What to do

Mark the sign-off stale on the RTM and propose a `CR-NNN`; do not record new approval.
Recording and promoting approval belongs to sw-review, which requires a configured
approver, the specific item, an HTTPS evidence URL and a matching hash.
