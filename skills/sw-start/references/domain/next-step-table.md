# next step table

`scripts/status.py` recommends the next skill and whose turn it is, from the feature
state and its signals. The suggestion is a route, not an approval.

## Recommendation rules (in the checker's order)

- Drift reported (`drift` not none/clean) → **review**; BA then PO.
- Open change requests → **sw-review**; PO.
- Open questions → **sw-review**; PO.
- Sign-off stale → **sw-review**; PO.
- State withdrawn/superseded → **sw-trace**; BA.
- `ready-for-dev` → **implementation**; Dev and QA.
- `ready-to-publish` with a fresh sign-off → **sw-publish**; BA after PO OK; otherwise **sw-review**; PO.
- `in-review` → **sw-review**; PO.
- `published` → **review**; BA.
- `draft` with a failing lint → **sw-spec**; BA; otherwise **sw-lint**; BA.

UNKNOWN means the report could not decide; treat it as an open question, not a fact.
