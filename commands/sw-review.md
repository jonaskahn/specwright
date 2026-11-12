---
name: sw-review
description: Runs a read-only review and records verifiable human approval, either the owner's plain accept or a formal sign-off with a hash-bound evidence link, before a draft can be planned or published. With no feature named it reviews every submitted feature together and asks once to accept the listed ones. Use when asked to review or accept FEAT-001, record PO sign-off, or decide whether CR-001 may proceed. Do NOT use to rewrite acceptance criteria (use sw-spec) or publish (use sw-publish).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-review/SKILL.md`. Treat this invocation as `/sw-review` and keep all runtime references anchored to that skill directory.
