# Choose the uncertainty before the notation

Use prose if fewer than five items with one actor communicate the same distinction.
The 45 primary types group variants (for example marimekko under treemap).
Every reference and asset below is relative to this loaded skill directory.

| Question / subject                               | Type reference                          | Production                                           |
|--------------------------------------------------|-----------------------------------------|------------------------------------------------------|
| Swimlane                                         | references/type-swimlane.md             | assets/swimlane.html · JSON                          |
| Flowchart                                        | references/type-flowchart.md            | assets/flowchart.html · JSON                         |
| Journey                                          | references/type-journey.md              | assets/journey.html · JSON                           |
| Service blueprint                                | references/type-service-blueprint.md    | assets/service-blueprint.html · JSON                 |
| Story map                                        | references/type-story-map.md            | assets/story-map.html · JSON                         |
| State                                            | references/type-state.md                | assets/state.html · JSON                             |
| Sequence                                         | references/type-sequence.md             | assets/sequence.html · JSON                          |
| Er                                               | references/type-er.md                   | assets/er.html · JSON                                |
| Components and explicit zones                    | references/type-architecture.md         | assets/architecture.html · JSON                      |
| Structural change with a change ledger           | references/type-architecture-delta.md   | assets/architecture-delta.html · JSON                |
| Department-owned existing systems                | references/type-it-current-state.md     | assets/it-current-state.html · JSON                  |
| Inputs and outputs across ordered stages         | references/type-process.md              | assets/process.html · JSON                           |
| Payloads moving across roles                     | references/type-data-flow.md            | assets/data-flow.html · JSON                         |
| Integration zones and protocols                  | references/type-dp-integration.md       | assets/dp-integration.html · JSON                    |
| Hosts, zones and replicas                        | references/type-deployment.md           | assets/deployment.html · JSON                        |
| Fan-in, shared dependencies and cycles           | references/type-dependency.md           | assets/dependency.html · JSON                        |
| Traceable parent-child decomposition             | references/type-tree.md                 | assets/tree.html · JSON                              |
| Reporting and named role ownership               | references/type-org-chart.md            | assets/org-chart.html · JSON                         |
| Containment and bounded scope                    | references/type-nested.md               | assets/nested.html · JSON                            |
| Ordered responsibility layers                    | references/type-layer-stack.md          | assets/layer-stack.html · JSON                       |
| A reinforcing closed feedback cycle              | references/type-loop.md                 | assets/loop.html · JSON                              |
| Hypotheses grouped around an observed effect     | references/type-fishbone.md             | assets/fishbone.html · JSON                          |
| Positioning against two normalized criteria      | references/type-quadrant.md             | assets/quadrant.html · JSON                          |
| Comparable series over scored criteria           | references/type-radar.md                | assets/radar.html · JSON                             |
| A cyclic category with quantitative magnitude    | references/type-polar.md                | assets/polar.html · JSON                             |
| Ordinal tiers or conversion funnel               | references/type-pyramid.md              | assets/pyramid.html · JSON                           |
| Parts of a quantitative whole                    | references/type-treemap.md              | assets/treemap.html · JSON                           |
| A bounded row/column intensity matrix            | references/type-heatmap.md              | assets/heatmap.html · JSON                           |
| Category amounts or paired comparisons           | references/type-bar.md                  | assets/bar.html · JSON                               |
| Cumulative increases and decreases               | references/type-waterfall.md            | assets/waterfall.html · JSON                         |
| Ordered values, ranks or distributions           | references/type-line.md                 | assets/line.html · JSON                              |
| Two normalized variables or distributions        | references/type-scatter.md              | assets/scatter.html · JSON                           |
| Value chain against evolution                    | references/type-wardley.md              | assets/wardley.html · JSON                           |
| Dated events and milestones                      | references/type-timeline.md             | assets/timeline.html · JSON                          |
| Dated work intervals                             | references/type-gantt.md                | assets/gantt.html · JSON                             |
| Overlapping membership sets                      | references/type-venn.md                 | assets/venn.html · JSON                              |
| Role-to-resource permission decisions            | references/type-dp-security-matrix.md   | assets/dp-security-matrix.html · JSON                |
| Quantities splitting and merging                 | references/type-sankey.md               | assets/sankey.html · JSON                            |
| A snapshot of work and WIP limits                | references/type-kanban.md               | assets/kanban.html · JSON                            |
| Attributes, operations and typed relationships   | references/type-uml-class.md            | assets/uml-class.html · JSON                         |
| Physical table columns and explicit multiplicity | references/type-db-schema.md            | assets/db-schema.html · JSON                         |
| Exploded axonometric                             | references/type-exploded-axonometric.md | assets/exploded-axonometric-template.html · template |
| Axonometric plan                                 | references/type-axonometric-plan.md     | assets/axonometric-plan-template.html · template     |
| Medallion                                        | references/type-medallion.md            | assets/medallion-template.html · template            |
| High level                                       | references/type-high-level.md           | assets/high-level-template.html · template           |

Architecture and charting explain supplied evidence; they do not authorize infrastructure, invent metrics or change the
source specification.
If behavior dominates, first read references/semantic-patterns.md; then use one layout grammar.
For ownership choose swimlane, for status choose state, for message order choose sequence.
For source impact and RTM facts, use the shared trace capability for evidence before drawing a dependency view.

Motion is on by default only where order or flow is the meaning (see references/motion.md): the flow
token on process, data-flow, dp-integration, flowchart, swimlane, state, loop and journey; message
stepping on sequence; a staggered entrance on bar, waterfall, gantt, sankey, timeline, line and the funnel
pyramid. Every other type, and all templates, stay static.
