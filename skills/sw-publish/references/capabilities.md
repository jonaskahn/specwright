# capabilities

sw-publish needs two capabilities, named before the first call.

## Required

- **jira-write** — the write path. Only sw-publish uses it. When the capability is
  absent, the skill stops at the dry-run and never writes.
- **jira-read** — reads the current remote state, identity candidates and the update
  timestamp before planning.

## Fallback

When a session tool provides neither, the bundled REST adapter (`scripts/kitlib`) is the
fallback only when installed. It is an integration seam, not a certification for a real
tenant; a project-limited service account with no delete permission is the safe shape for
a trial. Do not improvise credentials, and never read a token into a report.

## What this skill never does

- Never deletes a remote artifact or silently transitions a workflow state.
- Never retries an ambiguous create.
- Never publishes from a stored "yes" or a pasted approval claim.
