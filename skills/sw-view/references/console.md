# The console

A Svelte project, packed in `assets/console.zip`, built on the user's machine with Node 24
and served by `scripts/view.py`. It reads only `data/*.json`, which the server takes from
`_meta/data/`. It makes no other network request, and its page policy allows scripts, styles,
images, fonts and fetches from its own address only.

## Screens

| Group | Screen | Shows |
| --- | --- | --- |
| Workspace | Overview | Totals, items that need a person, state bar, lint gate. |
| | Projects | One card per project with counts and gate. |
| | Metrics | State, station, lint and objective measures worked out from the data. |
| Specs | Features | Every feature with its place on the lifecycle; filter and sort. |
| | Feature | Criteria, tasks, records, links, blockers and sign-off state. |
| | Tasks | Tasks by feature, with what each traces to. |
| | Board | Features by station with condition and blockers. |
| | Tree | Project, epic, feature, criterion and task as the graph links them. |
| Knowledge | Graph | Force graph with kind filters; a table with the same items. |
| | Query | find, show, neighbors, up, down, path, impact over the graph. |
| Governance | Records | Questions, decisions, change requests, amendments. |
| | Sources | Imported material and its age. |
| | Quality | Lint gate, results, findings and drift. |
| | Registry | Issued IDs; withdrawn IDs stay listed. |

Status is shown by a shape (circle with check, diamond, triangle, square, hollow circle) and
a word, never by colour alone. `Ctrl/Cmd+K` opens a palette that jumps to a screen or item and
runs queries. Theme, accent and density are kept in the browser (`specwright-*` keys).

## Queries

`find <text> [kind:feat] [status:open] [jira:KEY] [epic:EPIC-1]`, `show <name>`,
`neighbors <id> [in|out|both] [rel:has_ac] [declared]`, `up <id>`, `down <id> [depth:3]`,
`path <id> <id>`, `impact <id>`. They follow `graph.py`; golden files in the kit's tests
prove the two agree.

## Adapting it

The console in `<spec root>/console/` is ordinary source. `view.py dev` runs its dev server
with hot reload against the real data. Local edits are kept: `prepare` refuses to overwrite
them without `--force`. The data contract in `console/contract/` is generated from the
Python format and replaced on every upgrade.
