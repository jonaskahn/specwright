---
name: sw-plan
description: Turns accepted features into an implementation plan, layered tasks bound to the locked technology stack, and one self-contained prompt per task for an implementing agent (Claude Code or similar), with coverage and stack checks. With no feature named it plans every accepted feature still without a current plan. Use when asked to plan FEAT-001, break a story into tasks, lock or check the tech stack for tasks, prepare work or prompts for an AI agent or developer, or check that every AC has a task. Do NOT use for unreviewed ideas (use sw-shape), writing criteria (use sw-spec) or pushing tasks to Jira (not supported; tasks stay Markdown).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-plan/SKILL.md`. Treat this invocation as `/sw-plan` and keep all runtime references anchored to that skill directory.
