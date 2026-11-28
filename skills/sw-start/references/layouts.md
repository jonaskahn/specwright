# Layouts

The spec root is always the `.specwright/` folder of the repository. It holds `project.yaml`
(one project) or `workspace.yaml` (program). All spec paths are relative to it. There is no
standalone spec folder at the repository root; an older one is read so `workspace.py upgrade`
can move it.

| Shape | Manifest | Use when |
| --- | --- | --- |
| project | `.specwright/project.yaml` with `code: "."` | One project in the repository. |
| program | `.specwright/workspace.yaml` + `projects/<SCOPE>/project.yaml` | Several projects share one spec root; each project may set its own `code` folder (e.g. `services/orders`). |

Scope folders under each project, who writes them and what they hold. Nothing outside these
folders is read as evidence; `graph build` and the quality gate report any other top-level folder
(list extras in the manifest `ignore_folders`).

| Folder | Holds | Owner |
| --- | --- | --- |
| `00-inbox/` | `SRC-NNNN--slug.md` snapshots (immutable), `raw/` original bytes, `imports/<batch>/manifest.json` per import batch | sw-craft |
| `01-analysis/` | `ideas/`, `candidates/` (worker files and `assignment.tsv`), `baseline/` (the legacy register) | sw-craft |
| `epics/` | one folder per epic: `EPIC-NNN/EPIC-NNN--slug.md` | sw-craft |
| `features/` | one folder per feature: `FEAT-NNN.story.md`, `.card.md`, `.feature`, `review/`, `foundation/` | sw-craft |
| `tasks/` | one folder per feature: `FEAT-NNN.tasks.md`, `prompts/` (derived) | sw-craft writes the tasks, sw-forge the prompts |
| `plans/` | one folder per feature holding its implementation plan `FEAT-NNN.plan.md` | sw-forge |
| `records/` | questions, decisions, change requests, amendments | `record.py`, sw-craft, sw-craft |
| `diagrams/`, `assets/`, `snapshots/` | diagrams, user assets, remote snapshots | their capabilities |
| `.metadata/` | registry, RTM, write log, generated index and graph; `work/` is ephemeral, ignored by version control and the graph | shared scripts |

One folder per item is the address an agent works with. The graph, the console and the ready list
are the way to *find* an item; the folder is what to open once it is named:

    epics/EPIC-001/EPIC-001--refunds.md
    features/FEAT-001/FEAT-001.story.md
    features/FEAT-001/FEAT-001.card.md
    features/FEAT-001/review/FEAT-001.debate.md
    tasks/FEAT-001/FEAT-001.tasks.md
    tasks/FEAT-001/prompts/TASK-001-1.md
    plans/FEAT-001/FEAT-001.plan.md

Pictures stay in `diagrams/FEAT-001.*`; a story embeds one as `../../diagrams/<file>`.
`workspace.py upgrade` moves a project written with `02-drafts/`, `03-plan/` and
`01-analysis/epics/` to this layout (dry run first; `--apply` to move).

`AGENTS.md` holds the only copy of the standing rules; `CLAUDE.md` and `GEMINI.md` are one-line
pointers to it.

## Rules

- A folder with no git repository gets one, so a spec-only repository works the same way.
- A program manifest wins over nested project files when resolving the root.
- Link projects with qualified IDs such as `REF:EPIC-001`.
- Never write outside `.specwright/` unless asked. Merge the standing rules into
  an existing AGENTS.md only with the explicit merge option and a yes.
- `assets/` holds user-provided references; only the assets capability writes there.
