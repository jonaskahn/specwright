# Jira status sync (optional)

Files and git are the record. Jira mirrors status only when the project opts in.

## Opt in
Ask the owner once. On yes: `scripts/status_sync.py enable` (sets `jira.status_sync: true`).
Off again: `status_sync.py enable --off`. Story publication rules are unchanged; status sync
never edits text and never creates issues.

## Mapping (manifest `jira.status_map` overrides)
| Local state (from files) | Jira status |
| --- | --- |
| accepted (finalized) | To Do |
| planned (tasks ready) | Ready for Dev |
| shipped (change merged, or version 1 of a live feature) | Done |
| withdrawn / superseded without merge | Won't Do |
| spec, review | not synced |

## Run
1. `status_sync.py plan` → keys with `read`: read each with jira-read.
2. `status_sync.py plan --remote KEY=Status ...` → show the table and the token.
   `drift` rows (Jira says Done, files do not): report; never change local files from Jira.
3. On the owner's yes to that table: `status_sync.py confirm --confirm "<token>" --remote ...`.
4. `confirmed: true` → one jira-write transition per `transitions` row. No write tool → stop
   after the plan and say nothing was written.
