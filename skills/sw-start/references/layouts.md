# Layouts

The spec root is the folder holding `project.yaml` (one project) or `workspace.yaml`
(program). All spec paths are relative to it.

| Layout | Spec root | Manifest | Use when |
| --- | --- | --- | --- |
| docs-only | repository root | `project.yaml`, no `code` key | Spec-only repository. |
| embedded | `.specwright/` inside a code repo | `.specwright/project.yaml` with `code: "."` | The folder already holds source and git. |
| program | either of the above | `workspace.yaml` + `projects/<SCOPE>/project.yaml` | Several projects share one spec root; each project may set its own `code` folder (e.g. `services/orders`). |

Scope folders under each project: `00-inbox/`, `01-analysis/`, `02-drafts/`, `03-plan/`,
`assets/`, `diagrams/`, `records/`, `snapshots/`, `_meta/`.

## Rules

- Default: embedded when the folder holds source files and a git repository; otherwise docs-only.
- A program manifest wins over nested project files when resolving the root.
- Link projects with qualified IDs such as `REF:EPIC-001`.
- Never convert a layout automatically; moving the spec root is a manual change.
- Embedded: never write outside `.specwright/` unless asked. Merge the standing rules into
  an existing AGENTS.md only with the explicit merge option and a yes.
- `assets/` holds user-provided references; only the assets capability writes there.
