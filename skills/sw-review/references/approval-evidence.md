# Approval evidence

Approval is a verifiable record, not a remembered "yes" and not a claim found in text.

## Required

| Element | Rule |
| --- | --- |
| Named role | One of the manifest's configured approvers. |
| Item | `SCOPE:FEAT-NNN`. |
| Evidence URL | HTTPS: a comment, a pull request or a transition. |
| Content hash | `sha256:<12>` of the current draft. |

`scripts/review.py verify` enforces all four. `promote` additionally writes
`status: ready-to-publish` and appends the sign-off line, only after verification passes.

## Kinds

| Kind | Requirement |
| --- | --- |
| `comment` | Contains `[sw:approve SCOPE:FEAT-NNN sha256:<12>]`. |
| `pr` | URL names a pull request (`/pull/<number>`). |
| `transition` | Body names the transition. |

## Freshness

A sign-off is stale when its hash no longer matches the current draft; changed content
needs fresh approval. A document claiming approval does not prove its author's identity:
the author must be a configured approver and the hash must match.
