# Routing

Pick the first row that matches the evidence printed by the detection script.

| Evidence                                          | Next action                                                       | Why                                               |
|---------------------------------------------------|-------------------------------------------------------------------|---------------------------------------------------|
| No workspace, fresh work                          | Prepare, then Shape                                               | Nothing exists yet; shape the idea first.         |
| No workspace, user has documents                  | Prepare                                                           | Documents become saved source snapshots.          |
| No workspace, user has Jira issues                | Prepare (supplied baseline through normal ingestion)              | Issues become immutable snapshots.                |
| Workspace, graph missing                          | workspace upgrade (dry run, then --apply), then graph build       | Older workspaces gain the graph and new folders.  |
| Feature drafts in draft or in-review              | Lint, then Review                                                 | Approval is recorded only by Review.              |
| A feature is ready-to-publish                     | delivery-target prompt, then Publish                              | Ask Markdown, Jira or both unless already stored. |
| Published or ready-for-dev features without tasks | Plan                                                              | Agents need a plan and traceable tasks.           |
| Accepted idea, no feature drafts                  | Specify                                                           | Specify each accepted feature.                    |
| Draft idea, no features                           | Shape                                                             | Finish the split with the product owner.          |
| No sources, ideas or features                     | Prepare                                                           | Ask which the user has.                           |
| Anything else                                     | Status                                                            | Read the full position report.                    |

The user can supply a Figma link, diagram, mockup or raw idea at any time; the shared
assets capability stores it. That never replaces the route above.

Rules:

- Ask a question only when two rows fit and the evidence cannot separate them.
- Two scopes with different next actions: report both and ask which to continue.
- The route names an action; it never skips a gate such as lint, review or typed publish confirmation.
- A published-content request never triggers sync or reconciliation. A user-supplied
  baseline enters through normal ingestion; if its currency cannot be verified, stop.
