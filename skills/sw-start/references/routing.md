# Routing

Resolve the named item first, then read the fresh graph board for it. Do not apply a
scope-wide priority rule. A skill requested by name keeps that request and checks its
own prerequisites.

| Evidence | Route |
| --- | --- |
| No workspace | Confirm layout and setup, then the requested ingest or shape action. |
| Missing or incompatible graph schema | Show the upgrade dry-run; migrate only after agreement. |
| Stale graph | Rebuild as bounded maintenance; this is not a workspace upgrade. |
| Sources registered or imported, nothing shaped | Existing-baseline flow (references/brownfield.md); `action` names the step. |
| Several active candidates | Show the board and the ranked top three with reasons (advice only), then ask which item. |
| Draft epic or reopened slice | sw-shape. |
| One reserved accepted feature | sw-spec, not started. |
| Named draft, including open questions | sw-spec. |
| Submitted feature or invalidated approval | sw-review; only verified evidence promotes. |
| Reviewed feature without a current passing plan/tasks | sw-plan. |
| Passing plan, no publication request | Markdown delivery complete; stay in plan. |
| Explicit publication request, gates passing | Offer sw-publish; exact PUBLISH token still required. |
| Published feature, no tasks or task-only changes | sw-plan; never poll Jira. |
| Dashboard, overview, console, graph in a browser, metrics for the whole workspace | sw-view; it only reads and never advances a stage. |
| Published-text amendment | Stop until a current supplied baseline and a CR exist. |

Stored destination preferences never authorize writes or force publication. Ordinary
completion asks no destination question. Withdrawn IDs stay tombstones.
