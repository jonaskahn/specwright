---
name: sw-review
description: Finalizes stories before they are built. Shows the owner what they have not reviewed yet (changes since their last review, assumptions, open questions, existing-behaviour gaps), runs an independent review where separate reviewers (critic, builder, tester) challenge the draft with evidence and the author answers or fixes, then records the owner's finalize bound to the content hash. Use when asked to review, finalize, accept or approve FEAT-001, to challenge or stress-test a story, or to see what changed before accepting. Do NOT use to write or edit requirements (use sw-spec) or to publish (use sw-publish).
---

Load and follow the Specwright skill at `${CLAUDE_PLUGIN_ROOT}/skills/sw-review/SKILL.md`. Treat this invocation as `/sw-review` and keep all runtime references anchored to that skill directory.
