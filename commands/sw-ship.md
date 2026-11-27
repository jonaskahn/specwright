---
name: sw-ship
description: Publishes accepted epics, stories and tasks to Jira at the level the user chooses — one question for scope, a per-level dry-run, then execution only after a fresh explicit confirmation of the exact plan shown (a typed token, or a plain yes to that displayed plan), logging each remote call and every level locally. Never runs on its own. Use only when explicitly asked to ship or publish FEAT-001, its epic or its tasks, or to sync Jira status. Do NOT use for drafting or analysing (use sw-craft) or bulk Jira edits.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-ship/SKILL.md`. Treat this invocation as `/sw-ship` and keep all runtime references anchored to that skill directory.
