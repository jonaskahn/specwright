---
name: sw-ship
description: Publishes accepted epics, stories and tasks to Jira. Use only when explicitly asked to ship, publish, or sync Jira status. Requires a scope choice, a dry-run and fresh confirmation of the exact plan; records remote calls locally. Never starts automatically. Do NOT use for drafting, analysis or approval (use sw-craft), implementation plans (use sw-forge), or bulk Jira edits.
---

# sw-ship

Publish to Jira behind a scope question, a dry-run and a fresh yes to that exact plan. Optional:
no other skill runs it, and nothing is published unless the user asks now.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

Jira through the session jira-write tool only; then the registry, RTM Jira and drift columns,
card status and the local issue-type index (`references/field-ownership.md`).

## Steps

1. **Detect.** If the session carries a Jira connector, say so once and offer shipping. No
   connector → Markdown is the delivery; offer setup (`workspace.py jira set --site <url>
   --project-key <KEY>`). A stored preference is never permission.
2. **Scope.** Require an explicit publish request and accepted items with a current approval. Ask
   one question with the levels: epic only · story only · tasks only · epic + story + tasks ·
   nothing. Default: story only. Never assume all three.
3. **Plan.** `scripts/publish.py plan --feat FEAT-NNN --scope-id <S> --level epic|story|task` → a
   dry-run table per level: `EPIC-001 → create (Epic)`, `FEAT-004 → update (Story, hash …)`,
   `TASK-004-1 → create (Sub-task of PROJ-123)`. Exit 2 = blocked.
4. **Confirm.** Show the full plan and `PUBLISH <S>:FEAT-NNN <hash>`. On the user's fresh yes to
   that exact plan: `scripts/publish.py confirm --confirm <token> --hash <hash shown>`; false →
   stop. A remembered yes is never approval.
5. **Apply.** Execute through jira-write bound to the plan hash. No deletes, no forced
   transitions. An ambiguous create is never retried; check the remote state first.
6. **Record locally.** Registry rows for every level (`Jira key`, `Last published draft hash`,
   `State`), RTM Jira and drift columns, and each artifact's front matter. Drift is reported,
   never pulled.

Status sync (optional, opt-in): `references/status-sync.md`, at the story level.

## Stop when

Failed precondition, CONFLICT, identity ambiguity, ambiguous create, no write tool, no fresh yes,
no connector when the user asked for Jira.

## Finish

Run `_shared/scripts/finish.py --skill sw-ship --subject "<FEAT-NNN> publish record" --cwd <project>`.
Follow `_shared/references/handoff.md` for item selection, limits and every `handoff.mode`.
On `done`: Report what was created or updated per level and what stayed local.

## Load only when

| Need | File |
| --- | --- |
| Dry-run sections, levels, exit codes | references/dry-run-format.md |
| Owned fields, local updates, issue types | references/field-ownership.md |
| Publish protocol, remote read and baseline | references/publish-protocol.md |
| Tool capabilities | references/capabilities.md |
| Status-only sync of shipped and planned items | references/status-sync.md; scripts/status_sync.py --help |
| A step above is unclear or a script errors | references/procedure.md |
