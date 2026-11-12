---
name: sw-publish
description: Prepares one accepted Jira story change with identity checks, a dry-run and conflict stops, and executes it only after a fresh explicit confirmation of the exact plan shown (a typed token, or a plain yes to that displayed plan), logging each remote call. Use only when explicitly asked to publish FEAT-001 or push CR-001 to Jira. Do NOT use for drafting (use sw-spec) or bulk Jira edits.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-publish/SKILL.md`. Treat this invocation as `/sw-publish` and keep all runtime references anchored to that skill directory.
