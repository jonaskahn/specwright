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
| `approvers` | `role \| account_id` entries; only these may record approval. |
| `publish` | `transitions` (must stay false), `sandbox`, `attach_diagrams`. |
| `output` | `default`: `ask`, `markdown`, `jira` or `both`. |
| `confluence` | `spaces`: mapped page spaces. |
| `limits` | `child_depth`, `max_pages` for Confluence pulls. |

Create the manifest once; never overwrite it silently. An unsupplied value stays a
placeholder (`TBD`, empty list, `ask`) and reads as unknown, never as an authorized default.
