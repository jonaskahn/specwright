# Shared context

Specwright turns a software idea into implementation-ready work through five public skills
in two roles: sw-craft (BA) and sw-forge (Dev), with sw-start routing, sw-ship publishing and
sw-view reading. A story (BA/PO word) and a feature (Dev/QA word) are the same item, written
FEAT-NNN; never create a STORY identifier.

## Skills and owners

| Skill | Role | Owns |
| --- | --- | --- |
| sw-start | — | Detection, routing, workspace setup, guarded transitions, completion maintenance. |
| sw-craft | BA | Source snapshots, assets, candidate facts and conflicts; as-is analysis; the idea brief, INVEST split and FEAT reservation; story drafts, cards, diagrams, RTM draft columns and the task breakdown; the only recorder of approval (the owner's accept, or a formal sign-off). |
| sw-forge | Dev | The detailed implementation plan, task statuses and evidence, and the derived prompts. |
| sw-ship | — | The only writer to Jira or Confluence, at the level the user chooses. |
| sw-view | — | A read-only local web console over the workspace data; never advances an item. |

Knowledge, trace, lint, status, assets, visuals, data, citations and records are shared
capabilities; they are not stations.

Governance (optional or required sign-off; auto, guided or step flow; Markdown or Jira) is set
in the manifest; `governance.md` is the one table of what each setting allows. Stations hand
off to each other by `handoff.md`.

## Read order

1. sw-start/SKILL.md, then _shared/references/safety.md.
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
| Chip | A feature's illustration status: `needs illustration`, `no illustration`, `illustrated` or `check illustration`. sw-craft's illustration_check script prints it. |
| Spec root | The folder holding `project.yaml` (flat) or `workspace.yaml` (program). |
| Flat / program | Flat: one project at the spec root. Program: several projects under `projects/<SCOPE>/` that share a workspace. |
| Scope | The short name of one project, for example `REF`. Pass it as `--scope`; a program needs it for every write. |
| Scope root | One project's folder (the spec root when flat, `projects/<SCOPE>/` in a program). Its folders are `00-inbox/`, `01-analysis/`, `02-drafts/`, `03-plan/`, `records/`, `.metadata/`. |
| Active approval | An accept line or formal sign-off whose hash still matches the current story. A content change makes it stale. |
| Accepted | Stored status `ready-to-publish`, always shown as accepted. The approval then reads `accepted`, `signed-off` or `needs-signoff`. |
| Lead, worker | In a parallel batch the lead is the session agent that guards the writes and saves shared state; a worker is a sub-agent that writes one item's files. |
| Lint gate | `sw_lint.py --root <project> --gate draft\|review\|publish` (in `_shared/scripts` of the skills that lint). Exit 0 clean; 10, 20 or 30 means blocking findings at that gate. |
| DoR | The definition of ready for review: `dor.md`. |
| Business objective | `BO-NNN`. The outcome a feature exists for. A BO has many epics and features; an epic serves one or more BOs (`bo:` on the epic); a feature serves one or more BOs, directly in its own `bo:` or through its epic. |
| Visual reference | A mockup, Figma link, screenshot or diagram (asset kinds figma, mockup, image, diagram, or a drawing in `diagrams/`) that shows what to build. The story lists it in `assets:` and UI/UX; UI tasks cite it in `Visuals:`. |
| Layer | The delivery area of a task, written as a title prefix: backend, frontend, mobile, devops, data, qa, design or docs. One layer per task. |
| TRANSITION token | `TRANSITION <SCOPE>:FEAT-NNN <action> <digest>`, printed by sw-start's transition script preview. After the user's plain yes the agent passes it; the user never types it. |
| PUBLISH token | `PUBLISH <SCOPE>:FEAT-NNN <short-hash>`, printed by sw-ship's `publish.py plan`. |
