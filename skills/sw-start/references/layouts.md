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
| `01-analysis/` | `ideas/`, `epics/`, `candidates/` (worker files and `assignment.tsv`), `baseline/` (the legacy register) | sw-craft, sw-craft |
| `02-drafts/` | story drafts and cards | sw-craft |
| `03-plan/` | plans and tasks | sw-forge |
| `records/` | questions, decisions, change requests, amendments | `record.py`, sw-craft, sw-craft |
| `diagrams/`, `assets/`, `snapshots/` | diagrams, user assets, remote snapshots | their capabilities |
| `_meta/` | registry, RTM, write log, generated index and graph; `work/` is ephemeral, ignored by version control and the graph | shared scripts |

`AGENTS.md` holds the only copy of the standing rules; `CLAUDE.md` and `GEMINI.md` are one-line
pointers to it.

## Rules

- A folder with no git repository gets one, so a spec-only repository works the same way.
- A program manifest wins over nested project files when resolving the root.
- Link projects with qualified IDs such as `REF:EPIC-001`.
- Never write outside `.specwright/` unless asked. Merge the standing rules into
  an existing AGENTS.md only with the explicit merge option and a yes.
- `assets/` holds user-provided references; only the assets capability writes there.
