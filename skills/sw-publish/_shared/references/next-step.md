# Finish the requested action, not the whole pipeline

Run bounded completion maintenance, then read sw-start/scripts/start.py with --cwd
and --item when the feature is known. Resolve scripts against the loaded skill root.
When start.py reports a stale or missing graph, run the command it prints; every skill
ships `_shared/scripts/graph.py`.

Report the produced outputs and the named item's station/condition. Its siblings stay
where they are. A draft remains in spec, including open questions. A passing plan is
the Markdown delivery; do not suggest publication unprompted.

Resume unfinished work in the same station without repeating its entry confirmation.
Advancing into review, accepting a reopened split, entering plan, regenerating stale
tasks, or requesting publication requires the user's confirmation. Under `flow: guided`
a plain yes to "Continue to <next station>? (Y/n)" is enough for a local station; under
`flow: step` the user names the next one. It never counts as a formal sign-off under
required, and never as remote permission unless it answers the exact dry-run shown. A
route, stored preference, remembered yes or imported claim is never approval.

If several items are eligible, show the board and ask which one, including when they
share a station. A "push" or "publish" request goes to sw-publish when Jira is
configured; otherwise report that Markdown is delivered and offer the Jira setup.
