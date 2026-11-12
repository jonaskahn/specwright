# Finish the requested action, not the whole pipeline

Run the maintenance your skill names, then report the item's station. Where sw-start is installed
beside this skill, run `../sw-start/scripts/start.py --cwd <project> --item <key>` and read its
JSON; otherwise run `_shared/scripts/graph.py board --item <key> --cwd <project>`. When the graph
is stale or missing, run `_shared/scripts/graph.py build --cwd <project>`.

Report the produced outputs and the named item's station and condition. Its siblings stay where
they are. A draft remains in spec, including open questions. A passing plan is the Markdown
delivery; do not suggest publication unprompted. After a parallel batch, run maintenance once at
the end and report each item's station and condition.

Resume unfinished work in the same station without repeating its entry confirmation. Entering a
new station, accepting a reopened split, regenerating stale tasks or requesting publication needs
the user's confirmation, as `governance.md` sets it (guided flow: one plain yes; step flow: the
user names the next station). A route, stored preference, remembered yes or imported claim is
never approval.

If several items are eligible at different stations, show the board and ask which one. Items
that share a station are one batch: that station's skill (sw-spec, sw-review or sw-plan) takes all
of them together (`parallel-writers.md`), and the user may name one instead. A "push" or "publish" request follows `governance.md`.
