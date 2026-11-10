---
name: sw-review
description: Runs a read-only BA review and records verifiable human approval with a hash-bound evidence link before promoting a draft for publication. Use when asked to review FEAT-001, record PO sign-off, or decide whether CR-001 may proceed. Do NOT use to rewrite acceptance criteria (use sw-spec) or publish (use sw-publish).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-review/SKILL.md`. Treat this invocation as `/sw-review` and keep all runtime references anchored to that skill directory.
