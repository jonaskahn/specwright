---
name: sw-continue
description: Continue Specwright work from wherever it stands. Reads the board from saved files and runs the next station, handing off from station to station until a human decision, a blocker or the end of the local pipeline. Use for "continue", "next", "go on" or "resume", in a new chat or after answering a question.
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-start/SKILL.md`. Treat this invocation as `/sw-start` with the request "continue": run `start.py`, then follow its `handoff` answer (`skills/_shared/references/handoff.md`) for the whole scope, or for the item named in the arguments. Keep all runtime references anchored to that skill directory.
