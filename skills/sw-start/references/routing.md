# Routing

Pick the first row that matches the evidence printed by the detection script.

| Evidence                                          | Next skill                                                        | Why                                               |
|---------------------------------------------------|-------------------------------------------------------------------|---------------------------------------------------|
| No workspace, fresh work                          | sw-ingest, then sw-shape                                          | Nothing exists yet; shape the idea first.         |
| No workspace, user has documents                  | sw-ingest                                                         | Documents become saved source snapshots.          |
| No workspace, user has Jira issues                | sw-ingest with a supplied baseline                                | Issues become immutable snapshots.                |
| Workspace, graph missing                          | shared graph build after a dry-run workspace upgrade              | Older workspaces gain the graph and new folders.  |
| Feature drafts in draft or in-review              | shared lint, then sw-review                                       | Approval is recorded only by sw-review.           |
| A feature is ready-to-publish                     | delivery-target prompt, then sw-publish                           | Ask Markdown, Jira or both unless already stored. |
| Published or ready-for-dev features without tasks | sw-plan                                                           | Agents need a plan and traceable tasks.           |
| Accepted idea, no feature drafts                  | sw-spec                                                           | Specify each accepted feature.                    |
| Draft idea, no features                           | sw-shape                                                          | Finish the split with the product owner.          |
| No sources, ideas or features                     | sw-ingest or sw-shape                                             | Ask which the user has.                           |
| Anything else                                     | status capability                                                 | Read the full position report.                    |

The user can supply a Figma link, diagram, mockup or raw idea at any time; the shared
assets capability stores it. That never replaces the route above.

Rules:

- Ask a question only when two rows fit and the evidence cannot separate them.
- Two scopes with different next skills: report both and ask which to continue.
- The route names a skill; it never skips a gate such as lint, review or typed publish confirmation.
- A published-content request never triggers sync or reconciliation. A user-supplied
  baseline enters through normal ingestion; if its currency cannot be verified, stop.
