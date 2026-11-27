# sw-start — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

Step 0, before any Python: run `sh _shared/scripts/runtime.sh check` (Windows: `powershell
-NoProfile -File _shared/scripts/runtime.ps1 check`). It is a shell script because a Python
check cannot report that Python is missing. If Python is missing, step 7 applies before
anything else; every other step needs it.

1. Run scripts/start.py --cwd <user project>. Read its JSON: kit version, layout, spec
   root, mode, scopes, counts, graph freshness, output default, suggested skill and
   evidence. Per scope it also gives `signoff` (optional or required), `flow` (auto, guided or step)
   and `setup` (what the project still lacks; empty when nothing), and `handoff` (how the run
   goes on: `continue`, `confirm`, `stop` or `done`, with `next_skill` and `items`). Begin your reply with `Specwright <kit_version>`. Exit 2 with "incomplete or
   mixed install" means skill files are missing or from two releases: print the reinstall
   command it gives and stop. Exit 3 means a choice is required (for example two spec
   roots): list both, ask.
2. If a graph exists, read `_meta/READ-FIRST.md`, then run _shared/scripts/graph.py map
   for the scope and read the map. Look items up with graph.py show <any name or legacy
   ID>. Never crawl the workspace folders.
3. Route with references/routing.md. With no workspace, pick fresh or existing work and
   a layout from references/layouts.md: default embedded `.specwright/` when the folder
   holds code and git, otherwise docs-only. State the default and why.
4. State in two sentences: chosen skill, evidence, what it produces, then the JSON
   `action` as the one next step. For a named item run start.py --item <key> --pack and
   read the listed files in order, with the blocking questions first. When several items
   are active, show `ranking` (top three with reasons) as advice and let the user choose.
   When the route is `batch sw-craft`, `batch sw-craft` or `batch sw-forge` (two or more items of the scope, all
   in that station), take all of them in parallel (the default; the user may name one); the routed skill fans
   out per _shared/references/parallel-writers.md. "continue", "next", "go on" or "resume" with no item, and
   items spread over several stations, follow `handoff` instead of a choice: under `flow: auto` start
   its `next_skill` for its `items` (the whole scope, station by station: work that needs no answer first,
   questions last); show `ranking` only when `handoff.mode` is `stop`. Then read and follow
   ../<skill>/SKILL.md. If that file is absent (single-skill install), name the skill and
   ask for it to be invoked; do not search for it.
5. Ask at most five questions, each with options, consequences and a default (at most two
   at routing time). Ask for approvers (role, name, account ID; workspace.py approvers
   add) only when `signoff` is `required` and `setup` is not empty. Never ask what the
   script answered. Never infer approval, scope or a publish destination.
6. Delivery is Markdown; no destination question. On "push" or "publish": Jira configured
   -> sw-ship; not configured -> report that Markdown is delivered and offer
   `scripts/workspace.py jira set --site <url> --project-key <KEY>`. A stored value never authorizes a Jira write.
7. Runtimes: use the step 0 output (`runtime` in the start.py JSON agrees). Python is required:
   if it is missing, show `runtime.sh plan python` and ask once; after a yes run
   `runtime.sh install python --yes` (Linux package managers need sudo, so the script prints
   the command for the user to run). If Node is missing, say that only sw-view needs Node 24,
   show `runtime.sh plan node`, and ask once whether to install it. Run `runtime.sh install
   node --yes` only after the user approves that exact plan in this session
   (`_shared/references/runtime.md`). If they decline, everything else keeps working.
8. Workspace older than the graph schema: show the scripts/workspace.py upgrade dry-run;
   run with --apply only after the user agrees.

## Consumer check

Can a PO, developer or tester tell which skill runs, why, and the next human decision?
Name any UNKNOWN value instead of guessing.

## Stop and ask

Ask only what evidence does not settle (`_shared/references/stop-and-ask.md`; at most two
questions at routing time). Never choose a program default for a write.

## Gotchas

- Detection is read-only; writing starts in the routed skill.
- A route is not approval; only sw-craft records approval.
- STORY and FEAT are the same item. Write FEAT; say STORY only when echoing the user.
- A stored output default of jira is neither a publish request nor confirmation.
- In a code repository, never write outside `.specwright/` unless asked.
- Any public skill invoked by name checks its own prerequisites; do not reroute it. When it
  finishes it hands off by itself (`handoff.md`), so the chain continues from any entry point.
- The user's message always interrupts the chain: answer it, then resume from the board.
