# Choose the uncertainty before the notation

Run `scripts/illustration_check.py FEAT-NNN` first.

- **needs illustration** → pick a type below and draw.
- **no illustration** → write the paragraph. A dismissal already records the reason.
- **illustrated** → keep the picture.
- **check illustration** → the count is on the line, or a picture cites a withdrawn or missing ID. Decide, then draw or dismiss.

Prose or a picture follows the chip (`references/illustration-need.md`). A picture is drawn as
SVG and embedded in the story with `scripts/embed_diagram.py`.
Use only types whose reference file exists in this skill folder; `scripts/render_diagram.py
--list-types` prints the set this build supports. An absent type is not an error: pick the
nearest present type or write a paragraph. Never invent a notation; never ask the user to
install more types. Paths below are relative to the loaded skill directory.

| Question / subject                               | Type reference                          | Production                                           |
|--------------------------------------------------|-----------------------------------------|------------------------------------------------------|
| Who owns each step, and where does it hand off?  | references/type-swimlane.md             | assets/swimlane.html · JSON                          |
| Which decision sends two cases down two paths?   | references/type-flowchart.md            | assets/flowchart.html · JSON                         |
| How does one persona feel and act, stage by stage? | references/type-journey.md              | assets/journey.html · JSON                           |
| What does the actor see versus the work behind it? | references/type-service-blueprint.md    | assets/service-blueprint.html · JSON                 |
| How do activities break down into ordered stories? | references/type-story-map.md            | assets/story-map.html · JSON                         |
| Which states can one object be in, and what moves it? | references/type-state.md                | assets/state.html · JSON                             |
| In what order do messages pass between parties?  | references/type-sequence.md             | assets/sequence.html · JSON                          |
| Which entities exist and how are they related?   | references/type-er.md                   | assets/er.html · JSON                                |
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
