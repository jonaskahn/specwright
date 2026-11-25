---
name: sw-view
description: Opens a local, read-only web console over the workspace data: projects, metrics, features, tasks, a kanban board, the knowledge graph with its outline and queries, records, sources and quality. Use when asked to show a dashboard, open the console, see the graph, browse features or tasks, or view metrics for the whole workspace. Do NOT use to write or change requirements (use sw-spec), record approval (use sw-review) or publish (use sw-publish).
---

# sw-view

Open a local, read-only web console over `_meta/data/`. Not a station; never advances an item.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

Only `<spec root>/console/` (git-ignored). Never data files, specs or Jira.

## Steps

0. `sh _shared/scripts/runtime.sh check`.
1. `scripts/view.py doctor --cwd <project>` (exit 1 Node missing or console damaged; 4 data stale).
2. Node missing → show `runtime.sh plan node`; install only after a yes in this session.
3. Stale data → name the owning skill and offer its export; sw-view writes no data file.
4. `scripts/view.py prepare --cwd <project>`. Local changes in console/ → ask keep or `--force`.
5. Start `view.py serve --cwd <project>` in the background; give the printed address and how to stop.

## Stop when

Node not approved; console/ has local changes; packed console fails its checksum.

## Finish

Report the address and what each screen reads. Then return to the run (`start.py` `handoff`).

## Load only when

| Need | File |
| --- | --- |
| Screens and their data | references/console.md |
| Data format and owners | _shared/references/data-format.md |
| Runtime consent | _shared/references/runtime.md |
| A step above is unclear or a script errors | references/procedure.md |
