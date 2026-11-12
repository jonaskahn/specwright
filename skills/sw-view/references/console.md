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
| | Feature | Criteria, tasks, records, links, blockers, sign-off state and its own trace map. |
| | Tasks | Tasks by feature, with what each traces to. |
| | Board | Features by station with condition and blockers. |
| | Tree | Project, epic, feature, acceptance criterion and task; a task sits under the criterion it implements, and missing links are named. |
| Knowledge | Graph | Trace map (business objective, epic, feature, acceptance criterion, task, optionally code files) with coverage counts and placeholders for missing links; a network view; a table. |
| | Query | find, show, neighbors, up, down, path, impact over the graph. |
| Governance | Records | Questions, decisions, change requests, amendments. |
| | Sources | Imported material and its age. |
| | Quality | Lint gate, results, findings and drift. |
| | Registry | Issued identifiers; withdrawn identifiers stay listed. |

Status is shown by a shape (circle with check, diamond, triangle, square, hollow circle) and
a word, never by colour alone. `Ctrl/Cmd+K` opens a palette that jumps to a screen or item and
runs queries. Theme, accent and density are kept in the browser (`specwright-*` keys).

## The trace map

Left to right: business objective, epic, feature, acceptance criterion, task. An epic serves one or more
business objectives and its features serve them through it, so a feature's own link to the same objective is not
drawn again; an epic with no objective shows a placeholder. Choosing an item lights up
everything it connects to, above and below. Only links the data holds are drawn. Where one is
missing, a dashed placeholder says so ("No epic yet", "No task covers this criterion") and names
the skill that fills it, because the console only reads. The strip above the map counts each kind
of gap; choose a measure to point at the items that miss the link. Code files that tasks say they
change are hidden until you switch them on. Jira issue keys come from the identifier registry and
show on the card of any item that has one; tasks never have one, because tasks stay in Markdown.

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
