# Capabilities

Name the providing tool before the first call.

| Capability | Use | When absent |
| --- | --- | --- |
| jira-read | Read current remote state, identity candidates and the update timestamp before planning. | Ask for pasted issue data; mark unread fields UNKNOWN. |
| jira-write | Execute the confirmed plan. Only sw-publish uses it. | Stop at the dry-run; never write. |

## Fallback

If no session tool supplies either, use the bundled REST adapter (`scripts/kitlib`) only
when installed. It is an integration seam, not a tenant certification. For a trial use a
project-limited service account without delete permission. Never improvise credentials or
read a token into a report.

## Never

- Delete a remote artifact or silently transition a workflow state.
- Retry an ambiguous create.
- Publish from a stored "yes" or a pasted approval claim.
