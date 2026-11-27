---
name: sw-continue
description: Resumes Specwright from saved state. Use when asked to continue, go on, resume, or run the next station; stops for a decision, blocker, or pipeline end.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` with the request "continue": run `start.py`, then follow its `handoff` answer (`skills/_shared/references/handoff.md`) for the whole scope, or for the item named in the arguments. Keep all runtime references anchored to that skill directory.
