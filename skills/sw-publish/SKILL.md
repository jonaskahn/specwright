---
name: sw-publish
description: Prepares one accepted Jira story change with identity checks, a dry-run and conflict stops, and executes it only after a fresh explicit confirmation of the exact plan shown (a typed token, or a plain yes to that displayed plan), logging each remote call. Use only when explicitly asked to publish FEAT-001 or push CR-001 to Jira. Do NOT use for drafting (use sw-spec) or bulk Jira edits.
---

# sw-publish

Publish one accepted story to Jira behind a dry-run and a fresh yes to that exact plan.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

Jira through the session jira-write tool only; then registry, RTM Jira column, card status.

## Steps

1. Require an explicit publish request and an accepted story with a current approval. A plan is
   not needed: tasks are never published.
2. Read `references/publish-protocol.md`; do the remote read and baseline comparison it names.
3. `scripts/publish.py plan --feat FEAT-NNN --scope <S>` → dry-run (exit 2 = blocked).
4. Resolve identity from the registry first; a duplicate candidate stops the plan.
5. Show the full dry-run and `PUBLISH <S>:FEAT-NNN <hash>`. On the user's yes to that plan:
   `scripts/publish.py confirm --confirm <token>`; false → stop.
6. Execute through jira-write bound to the plan hash. No write tool → stop after the dry-run.
7. After every remote call succeeds, update the local index (`references/field-ownership.md`).

## Stop when

Failed precondition, CONFLICT, identity ambiguity, ambiguous create, no write tool, no fresh yes.

## Finish

Run `_shared/scripts/finish.py --skill sw-publish --subject "<FEAT-NNN> publish record" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Dry-run sections, exit codes | references/dry-run-format.md |
| Owned fields, local updates | references/field-ownership.md |
| Tool capabilities | references/capabilities.md |
| A step above is unclear or a script errors | references/procedure.md |
