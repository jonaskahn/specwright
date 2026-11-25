# Existing features: version 1, changes and fixes

All three are FEAT stories with the twelve sections; front matter says which kind.

## Version 1 of an existing feature (from sw-analyze, shape as-is or complete)
- After the owner confirmed the asked rows: `analyze.py confirm <target>`, then
  `scripts/merge.py v1 --feat FEAT-NNN --analysis <target>` (sets `origin: as-is`,
  `version: 1`, `analysis:`; refuses an unconfirmed analysis).
- ACs: only the rows confirmed done (cite the analysis rows in Context, not the code lines).
- Accepted version 1 needs no plan: it is already built. Gaps become a change.

## Change (`kind: change`) or fix (`kind: fix`)
Front matter: `kind: change|fix`, `changes: FEAT-TTT`, then run `scripts/merge.py base --change
FEAT-NNN` to record `base_hash`. The change's own ACs hold the new or corrected behaviour.
Add two subsections at the end of Context (the twelve sections stay canonical):

```markdown
### Delta

| Target | Action | Source |
| --- | --- | --- |
| AC-001-1 | change | AC-007-1 |
| new | add | AC-007-2 |
| AC-001-3 | remove | refunds by cheque dropped — DEC-004 |

### Must not change

AC-001-2, AC-001-4 — regression tests stay green.
```

- Actions: add (target `new`), change, remove (Source = reason), keep.
- A fix: one divergent row; Context says "code wrong: <analysis row, CODE cite>".
- Spec wrong, code right: no fix; correct the target story through review instead.
- Completion change (shape complete): Delta rows `add` for missing, `change` for partial.
- `merge.py check --change FEAT-NNN` before review: base current, rows valid, guards listed.

## Ship and merge (git is the record)
1. The user says it is shipped. Pre-ship check: `analyze.py new FEAT-NNN --verify` (one row
   per AC of the change), cite the code, `finish.py --skill sw-analyze --item FEAT-NNN.verify`.
2. `merge.py ship --change FEAT-NNN` refuses unless every AC row is done (or the owner gives
   `--accept-gaps "<reason>"`, kept as `ship_note`); records `root@commit` for each git code root.
3. Edit the target per Delta: copy changed/added AC text verbatim (new IDs continue the
   target's numbering), turn removed ACs into `~~AC-001-3~~ withdrawn — FEAT-NNN`, and copy
   the change's Business rules lines into the target's (replacing the rule they change).
4. `merge.py finish --change FEAT-NNN`: verifies the text, bumps `version`, adds a `changelog`
   line, marks the change `superseded` with `merged_into`. Old versions live in git history.
5. The target's text changed, so it returns to sw-review for the owner's finalize.
6. Jira status (optional, opt-in): see `../sw-publish/references/status-sync.md`.
