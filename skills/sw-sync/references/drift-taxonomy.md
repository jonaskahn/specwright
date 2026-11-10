# drift taxonomy

Drift classes come from `lib/kitlib/jira_diff.classify`, comparing the saved base
snapshot with the current remote state. Absent data stays absent; a class is reported
only when the comparison shows it.

## Classes

- `content-edited` — description or summary changed.
- `status-changed` — the Jira status name differs from the saved one.
- `comments-new` — a comment id appears that was not in the base.
- `links-changed` — issue links changed.
- `moved/deleted` — key, project changed or the issue is deleted.
- `linked-doc-version` — the mapped Confluence page version moved.
- `identity` — the stored identity mapping no longer matches.

## Handling

Report the classes on the RTM `Drift [sw-sync]` column. `content-edited` on a published
requirement means a change request (`CR-NNN`) is required before the local draft follows;
never edit a snapshot in place — a changed source is a new snapshot file.
