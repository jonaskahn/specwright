# Dry-run format

`scripts/publish.py plan` prints the three-way dry-run. Show it to the user before any
confirmation.

## Result fields

| Field | Meaning |
| --- | --- |
| `scope_id` | Resolved qualified feature id (`SCOPE:FEAT-NNN`). |
| `jira_key` | Target key, or `NEW` for a create. |
| `project` | Jira project from the manifest. |
| `draft_hash` | Full draft content hash. |
| `plan_hash`, `short_hash` | Bind the whole plan (sections, fields, links, attachments, calls), not just the draft. |
| `updated` | Remote update timestamp the edit is checked against. |
| `sections` | One row per story section: `base`, `current`, `new`, `action`. |

## Section actions

| Action | Meaning |
| --- | --- |
| `no-op` | Draft and remote agree; nothing to change. |
| `apply` | The draft changes the section safely; a diff is shown. |
| `keep-theirs` | Remote changed, draft did not; keep remote. |
| `CONFLICT` | Both sides changed the section; stop and ask a human. |

## Plan classification

The plan result carries `exit_code`, derived from the actions: `0` no write, `1` apply,
`3` sync needed (`keep-theirs` present), `4` conflict (`CONFLICT` present). A `CONFLICT`
blocks the plan; `keep-theirs` needs a fresh baseline from normal ingestion first.

This classification is separate from the process exit of scripts/publish.py: `0` the
preconditions pass and the plan is printed; `2` blocked plan or usage error.
