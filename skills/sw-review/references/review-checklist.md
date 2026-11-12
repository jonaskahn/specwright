# Review checklist

Run before recording or promoting an approval. Evidence shapes: `approval-evidence.md`.

## Always

- [ ] The draft is the resolved feature and its scope matches the manifest.
- [ ] The lint gate (`_shared/scripts/sw_lint.py --root <project> --gate review`) shows 0 blocking
      errors and `_shared/references/dor.md` is met.
- [ ] No acceptance criterion was rewritten during review; rewrites return to sw-spec.
- [ ] Advisory: note the illustration chip. A needs-illustration or check-illustration warning
      does not block approval.

## Accept (`signoff: optional`, the default)

- [ ] The user said yes in plain words to "accept FEAT-001?" for this exact feature, now.
- [ ] `scripts/review.py accept` wrote `ready-to-publish` (shown as accepted) and the line
      `self | accept | sha256:<12> | <date>`.

## Formal sign-off (the only path under `required`; optional under `optional`)

- [ ] The approver is in the manifest `approvers` list (account ID, role and name all match).
- [ ] The evidence URL is HTTPS and its kind is one of `comment`, `pr`, `transition`, or
      `chat` / `meeting` when the manifest `evidence.allowed_kinds` lists it (with `--session-ref`).
- [ ] The evidence hash matches the current draft hash.
- [ ] `scripts/review.py verify` exits 0, then `promote` writes the status and sign-off.

Any fail: stop and ask. Never hand-edit the status around the script; never promote or accept on
a stale hash.
