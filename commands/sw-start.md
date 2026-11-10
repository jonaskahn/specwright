---
name: sw-start
description: Guides users into Specwright. Detects the workspace layout and state, asks whether the work is fresh or existing, then loads and follows the matching sw-* skill. Use when a user starts out, is unsure which skill applies, makes a first-time or vague request such as "an idea to shape", "where to begin", "continue a spec" or "what comes next", or asks to push or ship work without naming a skill. Do NOT use when a specific skill is named (use that skill) or for writing, review or publishing itself.
---

Load and follow the Specwright skill at `\${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` and keep all runtime references anchored to that skill directory.
