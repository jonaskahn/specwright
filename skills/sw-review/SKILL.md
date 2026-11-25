---
name: sw-review
description: Runs a read-only review and records verifiable human approval, either the owner's plain accept or a formal sign-off with a hash-bound evidence link, before a draft can be planned or published. With no feature named it reviews every submitted feature together and asks once to accept the listed ones. Use when asked to review or accept FEAT-001, record PO sign-off, or decide whether CR-001 may proceed. Do NOT use to rewrite acceptance criteria (use sw-spec) or publish (use sw-publish).
---

# sw-review

Check drafts and record the owner's approval, bound to the content hash.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

Only the draft's status and sign-off line, through `scripts/review.py`.

## Steps

1. No feature named → every row of `_shared/scripts/graph.py board --station review --format json`.
2. Per feature, read-only and in parallel for a batch: `_shared/scripts/sw_lint.py --root <project>
   --gate review`, DoR (`_shared/references/dor.md`), INVEST.
3. Show one table: feature, title, verdict, short hash, blockers. Blocked features are not offered.
4. Ask once, with every other open question in the same message:
   "Accept FEAT-001, FEAT-003 (hashes shown)? yes / name a subset". Offer 2–3 ready replies.
5. On yes, per feature: `scripts/review.py accept --draft <file> --scope-id <S> --manifest <m>
   --hash <hash shown>`. Exit 2 = changed since shown: exclude and report.
6. `signoff: required` → a yes accepts nothing: `review.py verify`, then `promote` with evidence.

## Stop when

The accept question (this station's gate); unknown evidence kind, non-HTTPS URL, unconfigured
approver, hash mismatch.

## Finish

Run `_shared/scripts/finish.py --skill sw-review --subject "<FEAT-NNN> review" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Formal sign-off evidence | references/approval-evidence.md |
| Review run list | references/review-checklist.md |
| Gate table by sign-off mode | _shared/references/governance.md |
| A step above is unclear or a script errors | references/procedure.md |
