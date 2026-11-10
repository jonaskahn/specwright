# review checklist

Run before recording or promoting an approval.

- [ ] The draft is the resolved feature and its scope matches the manifest.
- [ ] The approver is in the manifest `approvers` list.
- [ ] The evidence URL is HTTPS.
- [ ] The evidence kind is comment, PR or transition and carries its required shape.
- [ ] The hash in the evidence matches the current draft hash.
- [ ] No acceptance criterion was rewritten during review; rewrites return to sw-spec.

When every item passes, `promote` writes the status and sign-off. When any item fails,
stop and ask — do not hand-edit the status around the script, and never promote on a
stale hash.
