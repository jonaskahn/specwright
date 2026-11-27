# Routing

Resolve the named item first, then read the fresh graph board for it. Do not apply a
scope-wide priority rule. A skill requested by name keeps that request and checks its
own prerequisites. Two roles, five skills:

| Station | Skill | What runs |
| --- | --- | --- |
| shape, spec, review | sw-craft | BA: sources, as-is, split, story, tasks, then review |
| plan | sw-forge | Dev: detailed plan per task, prompts, task status |
| publish | sw-ship | optional: Jira, only when asked |

| Evidence | Route |
| --- | --- |
| No workspace | Confirm layout and setup, then the requested step (sources, or an idea brief). |
| Missing or incompatible graph schema | Show the upgrade dry-run; migrate only after agreement. |
| Stale graph | Rebuild as bounded maintenance; this is not a workspace upgrade. |
| Sources registered or imported, nothing shaped | sw-craft intake and shape (references/brownfield.md); `action` names the step. |
| Code beside or inside the workspace, no specs yet; or a request to analyse, change, fix or complete existing behaviour | sw-craft as-is: register code roots, light inventory, then a gap table for the chosen feature. |
| "continue", "next", "go on", "resume" with no item | Follow `handoff` from `start.py` (`_shared/references/handoff.md`): under `flow: auto` run its `next_skill` for its `items`, station by station, until a human decision or a blocker. |
| Several active candidates at different stations | Under `flow: auto` the whole-scope run takes them station by station (`handoff`). Otherwise, or when `handoff` stops, show the board and the ranked top three with reasons (advice only), then ask which item. |
| Every active item in one station | Same skill for all: `start.py` answers `batch sw-<station>`; offer the batch in parallel (default) or one pick; sw-craft / sw-forge fan out one worker per FEAT (`_shared/references/parallel-writers.md`). |
| Draft epic or reopened slice | sw-craft shape. |
| One reserved accepted feature | sw-craft story, not started. |
| Named draft, including open questions | sw-craft story. |
| Submitted feature, stale or invalidated approval | sw-craft review; accept in plain words, or formal sign-off when `signoff: required`. |
| Accepted, tasks written, no current passing plan | sw-forge. |
| Passing plan, no publication request | Markdown delivery complete; stay in plan. The user may say "forge" for another feature. |
| Explicit publication request, accepted story | Jira configured: sw-ship (asks the level, then a dry-run, then a fresh yes). Otherwise Markdown is delivered; offer `scripts/workspace.py jira set --site <url> --project-key <KEY>`. |
| Published feature, wording change | sw-craft opens a `CR-NNN`; never an in-place edit. |
| Task status or evidence requested | sw-forge (`forge.py status` in its own folder). |
| Dashboard, overview, console, graph in a browser, metrics | sw-view; it only reads and never advances a stage. |
| Published-text amendment | Stop until a current supplied baseline and a current CR exist. |
| Withdrawn or superseded item | Excluded from the active board; its trace tombstone stays. |
| Conflicting decisions or an incomplete transaction | Unknown or blocked; inspect the evidence, never guess a route. |

Questions in a draft are specification work, not implicit submission. Several eligible items
require a target selection. Stored destination preferences never authorize writes or force
publication. Ordinary completion asks no destination question. Withdrawn IDs stay tombstones.
Whether to run on (`flow`) and how approval works (`signoff`): _shared/references/governance.md;
the hand-off after each station: _shared/references/handoff.md.
