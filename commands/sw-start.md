---
name: sw-start
description: Specwright's single entry. Detects the workspace and its state, routes to one of the public skills (sw-shape, sw-ingest, sw-spec, sw-plan, sw-review, sw-publish, sw-view), and tidies up after a step (assets, graph, trace, lint) before stopping at the next human decision. Use when starting Specwright, when unsure which sw- skill applies, or for any Specwright request that names no sw- skill. Do NOT use for writing requirements, recording approval or remote writes; those stay inside their owning skills.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` and keep all runtime references anchored to that skill directory.
