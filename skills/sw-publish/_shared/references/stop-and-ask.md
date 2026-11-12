# Resolve gaps without guessing

Read relevant artifacts before asking. Cite what you checked. Ask only about a real
gap, conflict or preference that the artifacts cannot settle. Record answers in
question and decision records so the next session does not ask again.

Ask at most five questions at once, everywhere; routing may ask fewer (sw-start asks at
most two at routing time). Use this shape:

> Q1 [blocking] Which refund window applies? Checked SRC-0001 and SRC-0002.
> A) 14 days -> the policy source needs amendment.
> B) 30 days -> the refund tiers need revision.
> Default if unanswered: leave Q-001 open; publication stays blocked.

Separate blocking decisions from assumptions that can be tested later. Save a non-blocking
unknown as a question with its default applied, list it in the summary and keep going; only a
blocker stops the run. The command, with every required flag:

```sh
_shared/scripts/record.py q new --title <text> --owner <role> --affects <FEAT-NNN> \
  --non-blocking --default <text> --status assumed
```

Run it from the project folder or add `--cwd <project>`; add `--scope <SCOPE>` in a program. Never invent approval or choose a project
scope for an external write just to keep moving.
