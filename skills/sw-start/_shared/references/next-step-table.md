# Per-item recommendations

The lifecycle evaluator supplies station and condition. Status may flag known drift and
open changes; it never polls Jira.

| Item evidence | Route |
| --- | --- |
| Draft including open questions | sw-spec |
| Explicitly reopened feature slice | sw-shape |
| In-review, stale or invalidated approval | sw-review |
| Accepted (`ready-to-publish`) with active approval | sw-plan |
| Missing/stale/invalid tasks or plan | sw-plan, blocked or incomplete |
| Passing plan, no publication request | plan complete, Markdown delivery |
| Accepted story and explicit publication request | sw-publish, still gated; a plan is not required |
| Published, task-only changes | sw-plan |
| Published-text change | supplied immutable baseline + CR before amendment |
| Withdrawn/superseded | excluded from active board; trace tombstone retained |
| Conflicting decisions or incomplete transaction | unknown/blocked; inspect evidence |

Questions in a draft are specification work, not implicit submission. A stored Jira
preference is not a publication request. Multiple items require a target selection. Under
the guided flow the agent offers each next route with one plain confirmation
(`governance.md`).
