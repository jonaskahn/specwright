# manifest schema

The flat manifest `project.yaml` (or the program `workspace.yaml` with one `projects/`
entry per scope) holds every field later skills resolve.

## Fields

- `scope` — 2–5 uppercase letters, the project id.
- `name` — the project display name.
- `code` — the code folder this project owns (embedded layout only).
- `jira` — `site`, `project_key`, `epic`; `TBD` until the user supplies them.
- `status_map` — the repository-to-Jira status mapping.
- `approvers` — `role | account_id` entries; only these may record approval.
- `publish` — `transitions` (must stay false), `sandbox`, `attach_diagrams`.
- `output` — `default`: one of `ask`, `markdown`, `jira`, `both`.
- `confluence` — `spaces`: mapped page spaces.
- `limits` — `child_depth` and `max_pages` for Confluence pulls.

## Rules

The manifest is created once and never silently overwritten. A value the user has not
supplied stays a placeholder (`TBD`, empty list, `ask`) and is treated as unknown, never
as an authorized default.
