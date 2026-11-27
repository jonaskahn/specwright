---
name: sw-forge
description: Turns an accepted story and its tasks into a very detailed, ready-to-apply implementation plan — exact files per task, the change itself, the test that proves it and the command that runs it — then writes one self-contained prompt per task and moves every task from not-started to planned. With no feature named it plans every accepted feature still without a current plan. Use when asked to plan FEAT-001 in detail, prepare a story for implementation, generate agent prompts or task order, or record a task as in-progress, done or blocked. Do NOT use for writing criteria or tasks (use sw-craft) or writing code.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-forge/SKILL.md`. Treat this invocation as `/sw-forge` and keep all runtime references anchored to that skill directory.
