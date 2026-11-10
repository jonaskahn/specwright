---
name: sw-sync
description: Pulls Jira issues and mapped Confluence pages into immutable snapshots, classifies drift, harvests candidate questions, marks stale sign-offs and proposes change requests. Use when asked what changed in PROJ-14, to sync Jira, check drift or pull a policy page. Do NOT use to edit Jira (use sw-publish) or decide approval (use sw-review).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-sync/SKILL.md`. Treat this invocation as `/sw-sync` and keep all runtime references anchored to that skill directory.
