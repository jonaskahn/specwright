# Resolve gaps without guessing

Read relevant artifacts before asking. Cite what you checked. Ask only about a real
gap, conflict or preference that the artifacts cannot settle. Record answers in
question and decision records so the next session does not ask again.

Ask at most five questions at once, everywhere; routing may ask fewer (sw-start asks at
most two at routing time). Rank them by blocking impact, then uncertainty, then rework cost.
Keep at most three clarification markers per document; move the rest into question records.
In a parallel batch the lead merges the workers' questions and asks five at a time. Use this shape:

> Q1 [blocking] Which refund window applies? Checked SRC-0001 and SRC-0002.
> A) 14 days -> the policy source needs amendment.
> B) 30 days -> the refund tiers need revision.
> Default if unanswered: leave Q-001 open; publication stays blocked.

Never apply a suggested answer without the user's choice. Save an unanswered question as
open. If any work depends on its answer, keep it blocking for those items and continue only
independent work. A truly non-blocking question uses `--non-blocking`, stays open and changes
no requirement. Never create `status: assumed` to keep moving. Finishing a station alone is
not a reason to ask (`handoff.md`), but a decision is due at any state. The command:

```sh
record.py q new --title <text> --owner <role> --affects <FEAT-NNN> \
  --status open --option "<choice and consequence>" --option "leave unresolved"
```

`record.py` lives in `_shared/scripts` of the skills that save questions. Run it from the project
folder or add `--cwd <project>`; add `--scope <SCOPE>` in a program. Never invent approval or choose a project
scope for an external write just to keep moving.

Offer "show evidence", "correct this", "change scope" and "leave unresolved" throughout the
workflow. Reuse an explicit answer only while its scope and evidence remain current; changed
sources or contradictory instructions require another confirmation. Recommendations may be
marked recommended, never preselected as authorization. Before an item has an ID, use ASK-n
in the provisional analysis; transfer it to a Q with the shared script once an item exists.
