---
name: sw-ship
description: Publishes accepted epics, stories and tasks to Jira. Use only when explicitly asked to ship, publish, or sync Jira status. Requires a scope choice, a dry-run and fresh confirmation of the exact plan; records remote calls locally. Never starts automatically. Do NOT use for drafting, analysis or approval (use sw-craft), implementation plans (use sw-forge), or bulk Jira edits.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-ship/SKILL.md`. Treat this invocation as `/sw-ship` and keep all runtime references anchored to that skill directory.
