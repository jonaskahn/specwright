# Layouts

The spec root is the folder holding `project.yaml` (one project) or `workspace.yaml`
(program). All spec paths are relative to it.

| Layout | Spec root | Manifest | Use when |
| --- | --- | --- | --- |
| docs-only | repository root | `project.yaml`, no `code` key | Spec-only repository. |
| embedded | `.specwright/` inside a code repo | `.specwright/project.yaml` with `code: "."` | The folder already holds source and git. |
| program | either of the above | `workspace.yaml` + `projects/<SCOPE>/project.yaml` | Several projects share one spec root; each project may set its own `code` folder (e.g. `services/orders`). |

Scope folders under each project, who writes them and what they hold. Nothing outside these
folders is read as evidence; `graph build` and the quality gate report any other top-level folder
(list extras in the manifest `ignore_folders`).

| Folder | Holds | Owner |
| --- | --- | --- |
| `00-inbox/` | `SRC-NNNN--slug.md` snapshots (immutable), `raw/` original bytes, `imports/<batch>/manifest.json` per import batch | sw-ingest |
| `01-analysis/` | `ideas/`, `epics/`, `candidates/` (worker files and `assignment.tsv`), `baseline/` (the legacy register) | sw-shape, sw-ingest |
| `02-drafts/` | story drafts and cards | sw-spec |
| `03-plan/` | plans and tasks | sw-plan |
| `records/` | questions, decisions, change requests, amendments | `record.py`, sw-ingest, sw-shape |
| `diagrams/`, `assets/`, `snapshots/` | diagrams, user assets, remote snapshots | their capabilities |
| `_meta/` | registry, RTM, write log, generated index and graph; `work/` is ephemeral, ignored by version control and the graph | shared scripts |

`AGENTS.md` holds the only copy of the standing rules; `CLAUDE.md` and `GEMINI.md` are one-line
pointers to it.

## Rules

- Default: embedded when the folder holds source files and a git repository; otherwise docs-only.
- A program manifest wins over nested project files when resolving the root.
- Link projects with qualified IDs such as `REF:EPIC-001`.
- Never convert a layout automatically; moving the spec root is a manual change.
- Embedded: never write outside `.specwright/` unless asked. Merge the standing rules into
  an existing AGENTS.md only with the explicit merge option and a yes.
- `assets/` holds user-provided references; only the assets capability writes there.
