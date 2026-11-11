# Choose the uncertainty before the notation

Use prose if fewer than five items with one actor communicate the same distinction.
Use only types whose reference file exists in this skill folder; `scripts/render_diagram.py
--list-types` prints the set this build supports. An absent type is not an error: pick the
nearest present type or write a paragraph. Never invent a notation; never ask the user to
install more types. Paths below are relative to the loaded skill directory.

| Question / subject                               | Type reference                          | Production                                           |
|--------------------------------------------------|-----------------------------------------|------------------------------------------------------|
| Swimlane                                         | references/type-swimlane.md             | assets/swimlane.html · JSON                          |
| Flowchart                                        | references/type-flowchart.md            | assets/flowchart.html · JSON                         |
| Journey                                          | references/type-journey.md              | assets/journey.html · JSON                           |
| Service blueprint                                | references/type-service-blueprint.md    | assets/service-blueprint.html · JSON                 |
| Story map                                        | references/type-story-map.md            | assets/story-map.html · JSON                         |
| State                                            | references/type-state.md                | assets/state.html · JSON                             |
| Sequence                                         | references/type-sequence.md             | assets/sequence.html · JSON                          |
| ER (entities and relationships)                  | references/type-er.md                   | assets/er.html · JSON                                |
| Inputs and outputs across ordered stages         | references/type-process.md              | assets/process.html · JSON                           |
| Payloads moving across roles                     | references/type-data-flow.md            | assets/data-flow.html · JSON                         |
| Structural change with a change ledger           | references/type-architecture-delta.md   | assets/architecture-delta.html · JSON                |
| Role-to-resource permission decisions            | references/type-dp-security-matrix.md   | assets/dp-security-matrix.html · JSON                |
| Components and explicit zones                    | references/type-architecture.md         | assets/architecture.html · JSON                      |
| Fan-in, shared dependencies and cycles           | references/type-dependency.md           | assets/dependency.html · JSON                        |
| Hosts, zones and replicas                        | references/type-deployment.md           | assets/deployment.html · JSON                        |
| Traceable parent-child decomposition             | references/type-tree.md                 | assets/tree.html · JSON                              |
| Reporting and named role ownership               | references/type-org-chart.md            | assets/org-chart.html · JSON                         |
| Dated events and milestones                      | references/type-timeline.md             | assets/timeline.html · JSON                          |
| Dated work intervals                             | references/type-gantt.md                | assets/gantt.html · JSON                             |
| A snapshot of work and WIP limits                | references/type-kanban.md               | assets/kanban.html · JSON                            |

Architecture and charting explain supplied evidence; they do not authorize infrastructure, invent metrics or change the
source specification.
If behavior dominates, first read references/semantic-patterns.md; then use one layout grammar.
For ownership choose swimlane, for status choose state, for message order choose sequence.
For source impact and RTM facts, use the shared trace capability for evidence before drawing a dependency view.

Motion is on by default only where order or flow is the meaning (see references/motion.md): the flow
token on process, data-flow, flowchart, swimlane, state and journey; message stepping on sequence; a
staggered entrance on gantt and timeline. Every other type stays static.
