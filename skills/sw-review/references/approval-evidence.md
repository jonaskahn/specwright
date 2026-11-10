# approval evidence

Approval is a verifiable record, not a remembered "yes" and not a claim found in text.

## What evidence must carry

- A **named role** that is one of the manifest's configured approvers.
- The **specific item** (`SCOPE:FEAT-NNN`).
- An **HTTPS evidence URL** — a comment, a pull request or a transition.
- A **matching content hash** — `sha256:<12>` of the current draft.

`scripts/review.py verify` enforces all four; `scripts/review.py promote` additionally
writes `status: ready-to-publish` and appends the sign-off line only after verification
passes.

## Kinds

- `comment` — must contain `[sw:approve SCOPE:FEAT-NNN sha256:<12>]`.
- `pr` — the URL must name a pull request (`/pull/<number>`).
- `transition` — the body must name the transition.

## Freshness

A sign-off is stale when its hash no longer matches the current draft. Changed content
needs fresh approval. A document claiming approval is not evidence of its author's
identity; the author must be a configured approver and the hash must match.
