# Finish the station, then hand off

End every station with `_shared/scripts/finish.py --skill <skill> --subject "<what changed>"
--cwd <project>` and act on `handoff.mode` (`handoff.md`). It replaces the manual steps in
`completion.md`: graph build, lint gate, stack check and agent prompts (sw-forge), style check,
data export, checkpoint, hand-off.

Between stations print only the one-line `say`. Report outputs once, at a stop or at done.
A named item moves alone; a bare command or "continue" moves the whole scope. A passing plan is
the Markdown delivery; never suggest publication unprompted. Approval, split acceptance and
publication still need the user's own answer (`governance.md`).
