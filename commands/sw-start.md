---
name: sw-start
description: Specwright's single entry. Briefs what the kit can do, detects the workspace, its state and the code's tech stack, asks a short prefilled intake on first run, routes to the right role skill (sw-craft for shaping, sources, analysis, stories, tasks and review; sw-forge for the detailed implementation plan; sw-ship for Jira; sw-view for the console), and keeps the run going from station to station, stopping only for a human decision or a blocker and never crossing from the BA role to the Dev role on its own. Use when starting Specwright, for help or a capability tour, for continue, next, go on or resume, to set or lock the tech stack, when unsure which sw- skill applies, or for any Specwright request that names no sw- skill. Do NOT use for writing requirements, recording approval or remote writes; those stay inside their owning skills.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` and keep all runtime references anchored to that skill directory.
