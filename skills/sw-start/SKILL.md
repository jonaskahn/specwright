---
name: sw-start
description: Specwright's single entry. Briefs what the kit can do, detects the workspace, its state and the code's tech stack, asks a short prefilled intake on first run, routes to the right public skill (sw-shape, sw-ingest, sw-spec, sw-plan, sw-review, sw-publish, sw-view), and keeps the run going from station to station, stopping only for a human decision or a blocker. Use when starting Specwright, for help or what can you do, for continue, next, go on or resume, to set or lock the tech stack, when unsure which sw- skill applies, or for any Specwright request that names no sw- skill. Do NOT use for writing requirements, recording approval or remote writes; those stay inside their owning skills.
---

# sw-start

Entry point. Read state from files, brief the user, set up, route, keep the run going.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Steps

0. `sh _shared/scripts/runtime.sh check` (Windows: `runtime.ps1 check`). No Python → step 6.
1. `scripts/start.py --cwd <project>`. Begin the reply with `Specwright <kit_version>`.
   Exit 2 → print its reinstall command, stop. Exit 3 → list the choices, ask.
2. First contact, "help" or "what can you do": print `start.py --brief` (≤ 10 lines).
3. No workspace (`fresh_setup`): ask the `intake` questions in one message (≤ 3, options,
   defaults; `references/intake.md`). Read back one line ("I will: …"), then
   `scripts/workspace.py init` with the layout and answers. Map "how far" to `--until`.
4. Existing code or an existing feature (`code.registered`/`code.detected`, a request to analyse,
   change, fix or complete something that exists) → `../sw-analyze/SKILL.md`. Gap shape decides
   what sw-spec writes. No code at all is fine: analysis then shows every criterion as missing.
5. Stack (`stack.status`): `missing` with code → `_shared/scripts/stack.py detect --write`, show
   the layers, ask lock/edit; `proposed` → show and ask once; on yes run
   `stack.py lock --confirm <hash shown>`. Docs-only and no answer → leave it; plan reports it.
6. Route by `handoff` (`references/routing.md`): `continue` → load `../<next_skill>/SKILL.md` for
   `items` now; "continue", "next", "resume" with no item → whole scope, station by station;
   a named item → `start.py --item <key> --pack`, read the listed files, run its station.
   `stop` → show the board, `ranking` as advice, ask.
7. Runtimes: Python missing → show `runtime.sh plan python`, install only after a yes. Node is
   only for sw-view; ask once (`_shared/references/runtime.md`).
8. Old graph schema → show `workspace.py upgrade` dry-run; `--apply` after a yes.
9. Push/publish request: Jira configured → sw-publish; else say Markdown is delivered and offer
   `workspace.py jira set --site <url> --project-key <KEY>`.

## Stop when

Choice of scope or spec root, setup answers, stack lock, runtime install, upgrade, or
`handoff.mode` is `stop`. At most two questions at routing time.

## Finish

Run `_shared/scripts/finish.py --skill sw-start --subject "<what changed>" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| First-run questions, read-back, suggested replies | references/intake.md |
| Route table, edge states | references/routing.md |
| Register or legacy baseline present | references/brownfield.md |
| Existing code or feature; gap shapes | ../sw-analyze/references/method.md |
| Layout choice; manifest fields | references/layouts.md; references/manifest-schema.md |
| Step-back, reset, guarded transitions | _shared/references/lifecycle.md; scripts/transition.py --help |
| Several items in one station | _shared/references/parallel-writers.md |
| Hand-off details, stop rules | _shared/references/handoff.md |
| Sign-off and flow settings | _shared/references/governance.md |
| A step above is unclear or a script errors | references/procedure.md |
