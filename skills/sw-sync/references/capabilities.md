# capabilities

sw-sync needs one read path, named before the first call.

## Required

- **jira-read** — pulls the issue, its comments and changelog. **jira-search** is used
  only when necessary, never by default.

## Fallback

The bundled REST adapter is the fallback when installed. When no read capability exists,
ask for pasted content, mark unread fields `UNKNOWN`, and do not claim a verified latest
baseline.

## What this skill never does

sw-sync never writes to Jira. It saves immutable local snapshots, classifies drift,
marks stale sign-offs and proposes change requests; publishing stays with sw-publish.
