---
name: sw-plan
description: Turns a reviewed feature into an implementation plan and traceable agent tasks, split per layer (backend, frontend, mobile, devops) with a layer prefix, each task tracing to acceptance criteria, rules, optional code paths and the mockups it builds, with a coverage check that flags stale tasks. With no feature named it plans every accepted feature still without a current plan. Use when asked to plan FEAT-001, break a story into tasks, prepare work for an AI agent or developer, or check that every AC has a task. Do NOT use for unreviewed ideas (use sw-shape), writing criteria (use sw-spec) or pushing tasks to Jira (not supported; tasks stay Markdown).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-plan/SKILL.md`. Treat this invocation as `/sw-plan` and keep all runtime references anchored to that skill directory.
