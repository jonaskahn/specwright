# Capabilities

Name the providing tool before the first call.

| Capability | Use | When absent |
| --- | --- | --- |
| jira-read | Read current remote state, identity candidates and the update timestamp before planning. | Ask for pasted issue data; mark unread fields UNKNOWN. |
| jira-write | Execute the confirmed plan. Only sw-publish uses it. | Stop at the dry-run; never write. |

## Fallback

If no session tool supplies jira-read, the bundled adapter `_shared/scripts/kitlib/jira_rest.py`
can read when `SPECWRIGHT_JIRA_SITE`, `SPECWRIGHT_JIRA_EMAIL` and `SPECWRIGHT_JIRA_TOKEN` are set
(check that they are set; never print them). Its command line is read-only. With no session
jira-write tool there is no shipped way to execute the plan: stop after the dry-run and say
so. The adapter is an integration seam, not a tenant certification. For a trial use a
project-limited service account without delete permission. Never improvise credentials or
read a token into a report.

## Never

- Delete a remote artifact or silently transition a workflow state.
- Retry an ambiguous create.
- Publish from a stored "yes" or a pasted approval claim.
