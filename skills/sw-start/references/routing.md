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
| Several active candidates at different stations | Show the board and the ranked top three with reasons (advice only), then ask which item. |
| Two or more reserved accepted features, or accepted features without a plan | Same skill for all: offer the batch in parallel (default) or one pick; sw-spec / sw-plan fan out one worker per FEAT (`_shared/references/parallel-writers.md`). |
| Draft epic or reopened slice | sw-shape. |
| One reserved accepted feature | sw-spec, not started. |
| Named draft, including open questions | sw-spec. |
| Submitted feature, stale or invalidated approval | sw-review; accept in plain words, or formal sign-off when `signoff: required`. |
| Accepted feature without a current passing plan/tasks | sw-plan. |
| Passing plan, no publication request | Markdown delivery complete; stay in plan. |
| Explicit publication request, accepted story | Jira configured: sw-publish (no plan needed; exact-plan confirmation still required). Otherwise Markdown is delivered; offer `scripts/workspace.py jira set --site <url> --project-key <KEY>`. |
| Published feature, no tasks or task-only changes | sw-plan; never poll Jira. |
| Dashboard, overview, console, graph in a browser, metrics for the whole workspace | sw-view; it only reads and never advances a stage. |
| Published-text amendment | Stop until a current supplied baseline and a CR exist. |

Stored destination preferences never authorize writes or force publication. Ordinary
completion asks no destination question. Withdrawn IDs stay tombstones. Whether to
run on (`flow`) and how approval works (`signoff`): _shared/references/governance.md.
