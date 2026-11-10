---
name: sw-start
description: Specwright's single entry. Detects the workspace and state, routes to one of the public skills (sw-shape, sw-ingest, sw-spec, sw-plan, sw-review, sw-publish), and runs bounded completion maintenance such as asset collection, graph refresh, trace updates and lint before stopping at the next human decision. Use when starting Specwright, when unsure which action applies, or for any request that names no action. Do NOT use for writing requirements, recording approval or remote writes themselves; those stay inside their owning actions.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` and keep all runtime references anchored to that skill directory.
