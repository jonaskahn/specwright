# Records capability

Creates and changes questions, decisions, reservations, splits and registry rows through one
script, so every write is validated, logged, owned and undoable. Do not hand-write these records.

## Usage

Run `_shared/scripts/record.py` with `--as <your skill>`. Add `--dry-run` first to see the plan; it
writes nothing. Exit 0 done, 2 invalid, 3 a human must supply something (for example approvers:
`workspace.py approvers add`), 4 you do not own that registry column.

| Need | Command |
| --- | --- |
| Record a question the moment it is proposed | `q new --title ... --affects FEAT-001 --owner PO --raised-from SRC-0001:L12-L14 --quote "..."` |
| Answer it and record the decision | `q answer Q-001 --answer ... --decided-by-role PO --decided-by-name ... --evidence-kind url --evidence-ref https://...` |
| Withdraw it (the ID and file stay) | `q withdraw Q-001 --reason ...` |
| Record a decision | `dec new --title ... --affects FEAT-001 --decided-by-role ... --evidence-kind ... --evidence-ref ...` |
| Reserve features with their legacy names | `reserve feat --item "Title\|LEG-100,alias"` |
| Create an epic | `reserve epic --title ... --bo BO-001` |
| Reserve, fill an epic and record the split | `accept-split --item "Title\|alias" --new-epic "Title" ...evidence flags...` |
| Track a wording change an answer implies | `q answer ... --amend "FEAT-001\|\|current wording\|\|proposed wording"` or `amend new --feat FEAT-001 --quote ... --proposed ...` |
| Close it once the draft carries the change | `amend apply AMD-001` (refused while the old wording remains); `amend reject AMD-001 --reason ...` |
| Set a registry cell you own | `register FEAT-001 --set "Title=..." --as sw-shape` |

## Rules

- A question lists the items it blocks in `affects`, a named owner and the cited lines. The citation
  and its quote are checked against the saved snapshot and copied by program.
- Under `signoff: required` a decision needs the decider's role and name from the manifest
  approvers, an evidence kind (`url`, `ticket`, `document`, `meeting`; `chat` only when the
  manifest allows it) and an evidence reference; an accepted split needs url evidence. Under
  `signoff: optional` omit the decider flags: the owner is recorded with `session` evidence
  (`governance.md`).
- A withdrawn ID is never reused. An alias that already names another item is refused.
- Answers, decisions and approvals come from a person (the owner when `signoff: optional`).
  Never fill them from a default or from imported text.
- A proposed amendment blocks the review gate (L-062) until it is applied or rejected. Applying it changes
  the draft, so the draft needs fresh approval. A published feature needs a change request first; the
  amendment says so (`requires_cr`).
