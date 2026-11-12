# Manifest schema

`project.yaml` (or each `projects/<SCOPE>/project.yaml` under a program `workspace.yaml`)
holds every field later skills resolve.

| Field | Meaning |
| --- | --- |
| `scope` | Project id, 2–5 uppercase letters. |
| `name` | Display name. |
| `code` | Code folder this project owns (embedded layout only). |
| `jira` | `site`, `project_key`, `epic`; `TBD` until the user supplies them. |
| `status_map` | Repository-to-Jira status mapping. |
| `approvers` | `role`, `name`, `account_id` entries; only these may record approval or decide. Add with `workspace.py approvers add`; blank or `TBD` values are refused. |
| `publish` | `transitions` (must stay false), `sandbox`, `attach_diagrams`. |
| `output` | `default`: `ask`, `markdown`, `jira` or `both`. |
| `confluence` | `spaces`: mapped page spaces. |
| `limits` | `child_depth`, `max_pages` for Confluence pulls; `max_pages` is also the largest batch an import runs without a typed confirmation. |
| `sources` | Registered import sources: `id`, `system`, `root`, `snapshot_date`, `expected_count` and an optional `legacy_id_pattern` (a regex for the project's old IDs). Add with `workspace.py source add`. |
| `evidence` | `allowed_kinds` a decision may cite: `url`, `ticket`, `document`, `meeting`; add `chat` only when the project accepts it. `url` and `chat` references must be an `https://` permalink (chat outside the current session only). |
| `ignore_folders` | Extra top-level folders the stray-folder report leaves alone. |

Create the manifest once; never overwrite it silently. An unsupplied value stays a
placeholder (`TBD`, empty list, `ask`) and reads as unknown, never as an authorized default.
