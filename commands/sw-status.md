---
name: sw-status
description: Computes a read-only position report for every feature, including state, gate result, linked Jira key, open records, drift, sign-off freshness and the next skill. Use when asked where the BA work stands, what blocks publication, or which story is ready for Dev. Do NOT use to repair findings (use sw-lint's owning skill) or publish (use sw-publish).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-status/SKILL.md`. Treat this invocation as `/sw-status` and keep all runtime references anchored to that skill directory.
