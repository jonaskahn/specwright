---
name: sw-ingest
description: Converts incoming business sources into hash-stamped Markdown snapshots, preserves original bytes, screens sensitive content, and identifies candidate facts and contradictions. Use when importing policy files, adding meeting notes or PO emails as evidence, or saving Jira issue JSON as background. Do NOT use for drafting stories or acceptance criteria (use sw-spec).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-ingest/SKILL.md`. Treat this invocation as `/sw-ingest` and keep all runtime references anchored to that skill directory.
