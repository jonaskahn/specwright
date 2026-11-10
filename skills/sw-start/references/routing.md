# Routing

Pick the first row that matches the evidence printed by the detection script.

| Evidence                                          | Next skill                                                     | Why                                               |
|---------------------------------------------------|----------------------------------------------------------------|---------------------------------------------------|
| No workspace, fresh work                          | sw-init, then sw-shape-idea                                    | Nothing exists yet; shape the idea first.         |
| No workspace, user has documents                  | sw-init, then sw-ingest                                        | Documents become saved source snapshots.          |
| No workspace, user has Jira issues                | sw-init, then sw-sync                                          | Issues become immutable snapshots.                |
| Workspace, graph missing                          | workspace upgrade (dry run, then --apply), then sw-graph build | Older workspaces gain the graph and new folders.  |
| Feature drafts in draft or in-review              | sw-lint, then sw-review                                        | Approval is recorded only by sw-review.           |
| A feature is ready-to-publish                     | delivery-target prompt, then sw-publish                        | Ask Markdown, Jira or both unless already stored. |
| Published or ready-for-dev features without tasks | sw-plan                                                        | Agents need a plan and traceable tasks.           |
| Published features                                | sw-sync                                                        | Check for drift against Jira.                     |
| Accepted idea, no feature drafts                  | sw-spec                                                        | Specify each accepted feature.                    |
| Draft idea, no features                           | sw-shape-idea                                                  | Finish the split with the product owner.          |
| No sources, ideas or features                     | sw-ingest or sw-shape-idea                                     | Ask which the user has.                           |
| Anything else                                     | sw-status                                                      | Read the full position report.                    |

The user can store a Figma link, diagram, mockup or raw idea at any time with sw-asset;
that never replaces the route above.

Rules:

- Ask a question only when two rows fit and the evidence cannot separate them.
- Two scopes with different next skills: report both and ask which to continue.
- The route names a skill; it never skips a gate such as lint, review or typed publish confirmation.
