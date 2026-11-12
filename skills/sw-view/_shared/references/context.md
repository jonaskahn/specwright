# Shared context

Specwright turns a software idea into implementation-ready work through eight public
skills. A story (BA/PO word) and a feature (Dev/QA word) are the same item, written
FEAT-NNN; never create a STORY identifier.

## Skills and owners

| Skill | Owns |
| --- | --- |
| sw-start | Detection, routing, workspace setup, guarded transitions, completion maintenance. |
| sw-ingest | Source snapshots, assets, candidate facts, conflicts. |
| sw-shape | Idea brief, INVEST feature split, FEAT reservation. |
| sw-spec | Story drafts, cards, diagrams, RTM draft columns. |
| sw-review | The only recorder of approval: the owner's accept, or a formal sign-off. |
| sw-plan | Implementation plan and tasks. |
| sw-publish | The only writer to Jira or Confluence. |
| sw-view | A read-only local web console over the workspace data; never advances an item. |

Knowledge, trace, lint, status, assets, visuals, data, citations and records are shared
capabilities; they are not stations.

Governance (optional or required sign-off, guided or step flow, Markdown or Jira) is set in
the manifest; `governance.md` is the one table of what each setting allows.

## Read order

1. sw-start/SKILL.md, then safety.md.
2. Route: the output of sw-start's start script and its routing reference.
3. Work: the routed skill's SKILL.md and the references it names.
4. Finish: completion.md, then the route table in sw-start's routing reference; stop at the next human
   decision.

## Terms

Keep IDs stable. Withdrawn IDs remain tombstones; their numbers are never reused. Store
external key mappings in the ID registry. Use qualified IDs (`SCOPE:FEAT-NNN`) across projects.

| Term | Meaning |
| --- | --- |
| Station | Where an item sits: `shape`, `spec`, `review`, `plan`, `publish`, or `inactive` (withdrawn or superseded). |
| Condition | The state inside a station: `not-started`, `in-progress`, `blocked`, `complete` or `unknown`. |
| Chip | A feature's illustration status: `needs illustration`, `no illustration`, `illustrated` or `check illustration`. sw-spec's illustration_check script prints it. |
| Spec root | The folder holding `project.yaml` (flat) or `workspace.yaml` (program). |
| Flat / program | Flat: one project at the spec root. Program: several projects under `projects/<SCOPE>/` that share a workspace. |
| Scope | The short name of one project, for example `REF`. Pass it as `--scope`; a program needs it for every write. |
| Scope root | One project's folder (the spec root when flat, `projects/<SCOPE>/` in a program). Its folders are `00-inbox/`, `01-analysis/`, `02-drafts/`, `03-plan/`, `records/`, `_meta/`. |
| Active approval | An accept line or formal sign-off whose hash still matches the current story. A content change makes it stale. |
| Accepted | Stored status `ready-to-publish`, always shown as accepted. The approval then reads `accepted`, `signed-off` or `needs-signoff`. |
| Lead, worker | In a parallel batch the lead is the session agent that guards the writes and saves shared state; a worker is a sub-agent that writes one item's files. |
| Lint gate | `sw_lint.py --root <project> --gate draft\|review\|publish` (in `_shared/scripts` of the skills that lint). Exit 0 clean; 10, 20 or 30 means blocking findings at that gate. |
| DoR | The definition of ready for review: `dor.md`. |
| TRANSITION token | `TRANSITION <SCOPE>:FEAT-NNN <action> <digest>`, printed by sw-start's transition script preview. After the user's plain yes the agent passes it; the user never types it. |
| PUBLISH token | `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`, printed by sw-publish's `publish.py plan`. |
