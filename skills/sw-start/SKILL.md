---
name: sw-start
description: Routes Specwright work from saved workspace state. Use when starting, requesting help, continuing or resuming, setting the stack, or naming no sw- skill. Handles setup and routes to sw-craft, sw-forge, sw-ship or sw-view; stops for decisions and blockers. Never crosses from BA to Dev without a request. Do NOT use for requirements or approval (use sw-craft), implementation plans (use sw-forge), or Jira writes (use sw-ship).
---

# sw-start

Entry point. Read state from files, brief the user, set up, route, keep the run going.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Steps

0. `sh _shared/scripts/runtime.sh check` (Windows: `runtime.ps1 check`). No Python → follow the Runtimes step before any Python command.
1. `scripts/start.py --cwd <project>`. Begin the reply with `Specwright <kit_version>`.
   Exit 2 → print its reinstall command, stop. Exit 3 → list the choices, ask.
2. First contact, "help" or "what can you do": print `start.py --brief` (≤ 10 lines).
3. No workspace (`fresh_setup`): ask the `intake` questions in one message (≤ 3, options,
   recommendations, never automatic answers; `references/intake.md`). Read back one line ("I will: …"), then
   `scripts/workspace.py init` with the layout and answers. Map "how far" to `--until`.
4. Adding or changing a feature in an existing project, with or without `.specwright/`:
   offer `context_intake` (discover docs/plans / selected files or items / describe first).
   Ask before scanning; no answer means no scan. On scan consent, load sw-craft and run
   `../sw-craft/scripts/analyze.py discover --cwd <repository> --confirm-scan` from sw-start.
   Follow `../sw-craft/references/repository-context.md` before drafting or linking anything.
   Existing work is reconciled, not replaced. On resume ask only about new gaps or changed evidence.
5. Stack (`stack.status`): `missing` with code → `_shared/scripts/stack.py detect --write`, show
   the layers, ask lock/edit; `proposed` → show and ask once; on yes run
   `stack.py lock --confirm <hash shown>`. Docs-only and no answer → leave it; plan reports it.
6. Foundation (new codebase: no code roots, `foundation.suggest` true): offer the foundation
   story once (`_shared/references/foundation.md`): check current tool guidance, ask
   `_shared/scripts/foundation.py questions` in one message, save answers (`foundation.py set`),
   reserve and draft it, continue in sw-craft. Declined → never offer again in this scope.
7. Route by `handoff` (`references/routing.md`): `continue` → load `../<next_skill>/SKILL.md` for
   `items` now; "continue", "next", "resume" with no item → whole scope, station by station;
   a named item → `start.py --item <key> --pack`, read the listed files, run its station.
   `stop` → show the board, `ranking` as advice, ask.
8. Runtimes: Python missing → show `runtime.sh plan python`, install only after a yes. Node is
   only for sw-view; ask once (`_shared/references/runtime.md`).
9. Old graph schema → show `workspace.py upgrade` dry-run; `--apply` after a yes.
10. Push/publish request, or "ship" / "forge" by name: Jira configured → sw-ship; else report Markdown delivery and offer
   `workspace.py jira set --site <url> --project-key <KEY>`.

## Stop when

Choice of scope or spec root, setup answers, stack lock, runtime install, upgrade, or
`handoff.mode` is `stop`. At most two questions at routing time.

## Finish

Run `_shared/scripts/finish.py --skill sw-start --subject "<what changed>" --cwd <project>`.
Follow `_shared/references/handoff.md` for item selection, limits and every `handoff.mode`.
On `done`: Report the resulting state.

## Load only when

| Need | File |
| --- | --- |
| First-run questions, read-back, suggested replies | references/intake.md |
| Route table, edge states | references/routing.md |
| Register or legacy baseline present | references/brownfield.md |
| Adopt an existing repository or add a feature; discovery and reconciliation | ../sw-craft/references/repository-context.md |
| Existing code or feature; gap shapes | ../sw-craft/references/method.md |
| Foundation story: tooling questions, Makefile, AGENTS.md | _shared/references/foundation.md |
| Layout choice; manifest fields | references/layouts.md; references/manifest-schema.md |
| Step-back, reset, guarded transitions | _shared/references/lifecycle.md; scripts/transition.py --help |
| Several items in one station | _shared/references/parallel-writers.md |
| Hand-off details, stop rules; role boundary | _shared/references/handoff.md |
| Sign-off and flow settings | _shared/references/governance.md |
| A step above is unclear or a script errors | references/procedure.md |
