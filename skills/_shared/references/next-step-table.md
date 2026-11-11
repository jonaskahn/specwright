# Per-item recommendations

The shared lifecycle evaluator supplies station and condition. Status may additionally
flag known drift and open changes for review; it never polls Jira to obtain them.

| Item evidence | Route |
| --- | --- |
| Draft including open questions | sw-spec |
| Explicitly reopened feature slice | sw-shape |
| In-review, stale or invalidated approval | sw-review |
| Ready-to-publish with active approval | sw-plan |
| Missing/stale/invalid tasks or plan | sw-plan, blocked or incomplete |
| Passing plan, no publication request | plan complete, Markdown delivery |
| Passing plan and explicit publication request | sw-publish, still gated |
| Published, task-only changes | sw-plan |
| Published-text change | supplied immutable baseline + CR before amendment |
| Withdrawn/superseded | excluded from active board; trace tombstone retained |
| Conflicting decisions or incomplete transaction | unknown/blocked; inspect evidence |

Questions in a draft are specification work, not implicit submission. A stored Jira
preference is not a publication request. Multiple items require a target selection.
