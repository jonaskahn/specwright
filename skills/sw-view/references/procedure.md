# sw-view — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

Step 0, before any Python: run `sh _shared/scripts/runtime.sh check` (Windows: `powershell
-NoProfile -File _shared/scripts/runtime.ps1 check`). A shell script, because a Python check
cannot report that Python is missing.

1. Run scripts/view.py doctor --cwd <project>. It reports Python, Node, the packed console,
   the console folder and any missing or stale data files. Exit 1 means Node 24 is missing
   or the packed console is damaged; exit 4 means data files are missing or stale (step 3).
   Typical output:

   ```
   python: 3.12.4 (ok)
   node: 24.1.0 (ok)
   console zip: ok (console <version>)
   console folder: not installed
   note: <a data file that is missing or stale, its owner and the command that refreshes it>
   ```
2. If Node is missing, follow _shared/references/runtime.md: show `runtime.sh plan node`,
   ask once, and run `runtime.sh install node --yes` only after the user approves that plan.
   If they decline, say sw-view needs Node 24 and stop; nothing else is affected.
3. If doctor lists missing or stale data files, name the skill that owns each one and offer
   to run that skill's export first. sw-view never writes a data file itself. The console
   still opens and shows an empty state that names the owner.
4. Run scripts/view.py prepare --cwd <project>. It unpacks the console, installs its
   dependencies once with `npm ci --ignore-scripts` (needs the network, part of the same
   approval) and builds it. Exit 3 means Node is missing (step 2). A refusal that names local
   changes means someone edited console/; ask whether to keep them (stop) or replace them
   (`--force`).
5. Start `view.py serve --cwd <project>` in the background and give the user the address it
   prints (`http://127.0.0.1:4173/` unless the port is busy). Tell them how to stop it. If they
   would rather run it themselves, print the serve command from `prepare`.
6. Report what the console shows and where each screen's data comes from. Do not describe
   numbers you have not seen.

## Consumer check

Can the user open the printed address and see their project with the counts that
`_shared/scripts/graph.py map` reports? Is `git status` free of `console/` and `.metadata/data/`?

## Stop and ask

Stop when Node is missing and not approved, when console/ holds local changes, and when the
packed console fails its checksum (reinstall the skill). Questions follow
`_shared/references/stop-and-ask.md`.

## Gotchas

- The page does not work when opened from disk (`file://`); the server is required.
- The server listens on 127.0.0.1 only and answers GET and HEAD for the console, the data files
  and, under `/doc/<project>/`, a project's Markdown, PDF, image and link files for the preview
  panel; it refuses dot-files, machine files and anything outside the project. A static
  server started after `prepare --copy-data` shows the data but not file contents; use
  `view.py serve` to read documents.
- The data files hold metadata only: identifiers, titles, statuses, paths and links. Body text and
  names of approvers are not in them.
- The stored status `ready-to-publish` is shown as **accepted**; say accepted to readers.
- `docs/console/` sits inside a docs folder. A docs-site generator that scans the folder
  should exclude `console/`.
- Another process may already use the port; the server takes the next free one and prints it.
