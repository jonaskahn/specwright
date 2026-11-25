---
name: sw-review
description: Finalizes stories before they are built. Shows the owner what they have not reviewed yet (changes since their last review, assumptions, open questions, existing-behaviour gaps), runs an independent review where separate reviewers (critic, builder, tester) challenge the draft with evidence and the author answers or fixes, then records the owner's finalize bound to the content hash. Use when asked to review, finalize, accept or approve FEAT-001, to challenge or stress-test a story, or to see what changed before accepting. Do NOT use to write or edit requirements (use sw-spec) or to publish (use sw-publish).
---

# sw-review

Finalize, not a click-through. The owner sees what is new to them, independent reviewers
challenge the draft, and only then does the owner finalize the exact hash shown.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`02-drafts/review/FEAT-NNN.{pack,brief,debate}.md`; fixes to the draft (as the author, within
the story's own scope); the draft's status and sign-off line through `scripts/review.py`.

## Steps

1. No feature named → every row of `graph.py board --station review --format json`. Machine
   gates first: `_shared/scripts/sw_lint.py --gate review`, DoR. A failing gate goes back to sw-spec.
2. Independent review per feature (`references/debate.md`):
   - `scripts/debate.py brief --feat FEAT-NNN` and `debate.py start --feat FEAT-NNN`
     (`--independence same-session` when no subagents are available).
   - Run three reviewers (critic, builder, tester), each a separate subagent given only the
     brief; no chat history, no authoring notes. In parallel for a batch.
   - Put their rows in the debate Findings table. As the author answer each: `accepted` (fix the
     draft), `rebutted` (evidence), or `open` (`record.py q new` or `owner`).
   - Round 2: the same reviewers see the answers and mark rebuttals `holds` or `withdrawn`.
     No new findings. Then `debate.py seal`, `debate.py check`.
3. `scripts/debate.py pack --feat FEAT-NNN` and show the pack: what it promises, what is new to
   the owner (diff since their last finalize or the whole story), assumptions and open
   questions, existing-behaviour gaps, debate outcome and every dispute still standing.
4. The stop: ask once, for the batch, with the disputes and questions in the same message:
   "Finalize FEAT-001 (hash …)? — yes / send back with notes / answer Q-…". Offer 2–3 ready replies.
5. Finalize per feature: `scripts/review.py accept --draft <file> --scope-id <S> --manifest <m>
   --hash <hash shown>`. It refuses without a passing debate check; the owner may finalize anyway
   with `--skip-debate "<reason>"` (recorded). `signoff: required`: `verify`, then `promote`.
6. Send back → sw-spec with the owner's notes; the debate record stays for the next round.

## Stop when

Only the finalize question (step 4), plus formal sign-off evidence under `signoff: required`.
Reviewers and author resolve everything else between themselves first.

## Finish

Run `_shared/scripts/finish.py --skill sw-review --subject "<FEAT-NNN> finalize" --cwd <project>`
(add `--item` per feature). Finalized features continue to sw-plan; a version 1 of an existing
feature is complete (already built); a merged target returns here after its change ships.

## Load only when

| Need | File |
| --- | --- |
| Debate roles, rounds, severity, independence | references/debate.md |
| Formal sign-off evidence | references/approval-evidence.md |
| Gate table by sign-off mode | _shared/references/governance.md |
| A step above is unclear or a script errors | references/procedure.md |
