---
name: sw-start
description: Specwright's single entry. Detects the workspace and its state, routes to one of the public skills (sw-shape, sw-ingest, sw-spec, sw-plan, sw-review, sw-publish, sw-view), and keeps the run going from station to station on its own, stopping only for a human decision or a blocker. Use when starting Specwright, for "continue", "next", "go on" or "resume", when unsure which sw- skill applies, or for any Specwright request that names no sw- skill. Do NOT use for writing requirements, recording approval or remote writes; those stay inside their owning skills.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` and keep all runtime references anchored to that skill directory.
