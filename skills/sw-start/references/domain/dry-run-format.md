# dry-run format

`scripts/publish.py plan` prints the three-way dry-run that must be shown to the user
before any confirmation. Read this to interpret its output.

## Result fields

- `scope_id` — the resolved qualified feature id (`SCOPE:FEAT-NNN`).
- `jira_key` — the target key, or `NEW` for a create.
- `project` — the Jira project from the manifest.
- `draft_hash` — the full draft content hash; `plan_hash` / `short_hash` bind the whole
  plan (sections, fields, links, attachments, calls), not just the draft.
- `updated` — the remote update timestamp the edit will be checked against.
- `sections` — one row per story section with `base`, `current`, `new` and an `action`.

## Actions

- `no-op` — draft and remote already agree; nothing to change.
- `apply` — the draft changes the section safely; a diff is shown.
- `keep-theirs` — the remote changed and the draft did not; keep remote.
- `CONFLICT` — both sides changed the same section; stop and ask a human.

Exit codes: `0` no write, `1` apply, `3` sync needed, `4` conflict. Any `CONFLICT`
blocks the plan; `keep-theirs` means a sync is needed first.
