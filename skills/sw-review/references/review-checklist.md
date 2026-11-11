# Review checklist

Run before recording or promoting an approval.

- [ ] The draft is the resolved feature and its scope matches the manifest.
- [ ] The approver is in the manifest `approvers` list.
- [ ] The evidence URL is HTTPS.
- [ ] The evidence kind is comment, PR or transition and carries its required shape.
- [ ] The evidence hash matches the current draft hash.
- [ ] No acceptance criterion was rewritten during review; rewrites return to sw-spec.

All pass: `promote` writes the status and sign-off. Any fail: stop and ask. Never
hand-edit the status around the script; never promote on a stale hash.
