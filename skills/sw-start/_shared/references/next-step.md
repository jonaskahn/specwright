# Finish the station, then hand off

Run the maintenance your skill names, then decide what comes next from the board, never from
memory:

```sh
_shared/scripts/handoff.py next --cwd <project> --done <this skill> [--item <key>] [--until <station>]
```

Act on its `mode` as `handoff.md` says: `continue` loads the next skill now (under `flow: auto`
no question is asked), `confirm` asks one "Continue to <next>? (Y/n)" (`flow: guided`), `stop`
asks the user what is needed, `done` reports the Markdown delivery. Where `handoff.py` is absent
(an older single-skill install), run `../sw-start/scripts/start.py --cwd <project> --item <key>`
and read its `handoff` field, or `_shared/scripts/graph.py board --item <key> --cwd <project>`.

Report outputs once, at the stop or at done; between stations print only the one-line `say`.
Siblings move only when the run covers the whole scope (a bare command or "continue"); a named
item moves alone. A draft with an open blocking question stays in spec and waits for the answer.
A passing plan is the Markdown delivery; do not suggest publication unprompted. After a
parallel batch, run maintenance once at the end and hand off the batch together.

Resume unfinished work in the same station without repeating its entry. Approval, accepting a
split or reopened slice, regenerating stale tasks that would change a reviewed plan, and any
publication still need the user's own answer (`governance.md`). A route, stored preference,
remembered yes or imported claim is never approval.

Items that share a station are one batch: that station's skill (sw-spec, sw-review or sw-plan)
takes all of them together (`parallel-writers.md`), and the user may name one instead. A "push"
or "publish" request follows `governance.md`.
