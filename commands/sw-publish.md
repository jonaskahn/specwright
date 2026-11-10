---
name: sw-publish
description: Prepares and, only after explicit typed confirmation, executes one reviewed Jira story change with identity checks, a three-way dry-run, conflict stops and an intent log. Use only when explicitly asked to publish FEAT-001 or push CR-001 to Jira. Do NOT use for drafting (use sw-spec) or bulk Jira edits.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-publish/SKILL.md`. Treat this invocation as `/sw-publish` and keep all runtime references anchored to that skill directory.
