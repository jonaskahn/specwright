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
| Specs | Features | Every feature with its place on the lifecycle; View reads the story. |
| | Feature | Criteria, tasks, records, links, blockers, sign-off state and its own trace map. |
| | Tasks | Tasks by feature, with what each traces to. |
| | Board | A kanban board: one column per station, one card per feature with its epics, criteria and tasks by layer, open questions, blockers, who is next and how long it has been idle. Filters, swimlanes by project, epic or turn. Read-only: a card shows the command that moves it on. |
| Knowledge | Graph | One page: an outline beside the trace map (business objective, epic, feature, acceptance criterion, task, optionally code files), with coverage counts and placeholders for missing links; a network view; a table; the outline full width. A project select shows one project at a time, each project in turn, or only the links across projects. |
| | Query | find, show, neighbors, up, down, path, impact over the graph. |
| Governance | Records | Questions, decisions, change requests, amendments. |
| | Sources | Imported material and its age. |
| | Quality | Lint gate, results, findings and drift. |
| | Registry | Issued identifiers; withdrawn identifiers stay listed. |

Status is shown by a shape (circle with check, diamond, triangle, square, hollow circle) and
a word, never by colour alone. `Ctrl/Cmd+K` opens a palette that jumps to a screen or item and
runs queries. Theme, accent and density are kept in the browser (`specwright-*` keys).

## Preview and tables

Pressing View on a table row or board card, or the eye on a graph card or outline row, opens the
preview on the right (choosing a graph card only lights its chain): the item's Markdown file with its own line marked, a PDF in the browser's viewer, an image,
or a link file's address as text. It has an outline of the document, a Connections tab with the
graph's links, and a Details tab. The address keeps the choice (`?pk=REF:AC-001-2`), so a reload or
a pasted link returns to it; Esc closes it and the dock button keeps it beside the page. Markdown
is drawn from a small reader that never produces HTML: raw HTML in a document stays text, and only
`http`, `https` and `mailto` links are followed. Documents come from the server's `/doc/` route, so
file contents need `view.py serve`.

A diagram that sw-spec drew is an SVG, embedded in its story as an image under UI/UX: it shows
inline in the story's preview, and clicking it opens the file at full width. A feature's Details
tab lists its pictures, so one that is drawn but not yet embedded (an approved story) is still one
click away. An HTML diagram is not previewed; only Markdown, PDF and images open.

Every table has a filter, facet selects, sortable headers and pages of 25, 50 or 100 rows, and its
state is kept in the address (`t.<table>.q`, `.f.<column>`, `.s`, `.p`, `.n`).

## The graph page

The select at the top of the page chooses one project, each project in turn, or the links across
projects. A project's graph also shows the epics and objectives of other projects that its features
belong to, dashed and labelled with their project, so a link across projects is drawn instead of
reported as missing. The outline on the left (also the Outline view, and where the old `#/tree`
address goes) selects the same item as the map.

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
