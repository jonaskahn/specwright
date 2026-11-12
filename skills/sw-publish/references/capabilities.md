# Capabilities

Definitions of `jira-read`, `jira-search`, `jira-write` and the read-only fallback adapter live in
`_shared/references/capabilities/remote.md`. Name the providing tool before the first call.

sw-publish uses `jira-read` for the remote read the plan needs, and `jira-write` to execute the
confirmed plan. With no session `jira-read` tool, ask for pasted issue data. With no session
`jira-write` tool there is no shipped way to write: stop at the dry-run and say that nothing was
written. For a trial use a project-limited service account
without delete permission. Never improvise credentials or read a token into a report.

## Never

- Delete a remote artifact or silently transition a workflow state.
- Retry an ambiguous create.
- Publish from a stored "yes" or a pasted approval claim.
