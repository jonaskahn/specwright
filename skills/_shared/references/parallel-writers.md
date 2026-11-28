# Parallel writers

Use this when two or more independent items (features) wait at the same station in one
scope and the host can run sub-agents. It gives speed without shared-write races.

## When

- Fan out for 2+ items: reserved features to specify, accepted features to plan, submitted
  features to prepare for review. For review the workers only check; accepts stay with the lead
  (sw-craft "Several features").
- Stay serial for one item, an amendment of published text (CR and snapshot gate), a scope
  that is ambiguous, or a host without sub-agents. Say which, in one line.
- One worker per item. Run up to 8 at a time; the rest follow in the next wave.
- Workers on items that share a decision wait until the lead has recorded it, so no two
  workers invent different rules.

## Delegation environment

Use shared-workspace workers with the file ownership and guard below. Do not request Git
worktree isolation for a docs-only workspace. If isolation is needed, first verify that the
target is a Git repository or that the host supports another isolation mechanism.
A worktree-unavailable error means the worker did not start: do not retry the same call.
Omit isolation if the host allows it; otherwise execute serially in the current workspace.
Do not initialize Git or configure hooks solely to make delegation work.

## Rules

1. **One writer per file.** A worker owns its item's files only (the skill names them).
   It never writes records, registry rows, RTM, graph, `.metadata/data/`, status, snapshots,
   or a sibling's files.
2. **The lead owns shared state** and writes it once, after the workers (and commits once with
   `checkpoint.py`; a worker never does): questions
   (`record.py q new`), ID reservations, RTM columns through the trace capability, graph
   build, data exports, lint, status. The lead reserves any new BR/NFR/FR IDs before
   briefing; a worker never allocates one.
3. **Brief minimal:** item ID, scope root, its `graph.py context` pack, the skill's
   references, the untrusted-content rule. No sibling drafts. A cross-item rule comes from
   the lead as a cited decision.
4. **Exactness by program:** citations from `cite.py stamp`, hashes from `spec_hash.py`;
   a worker never retypes either.
5. **Guard the writes.** Before launching:
   `_shared/scripts/parallel_guard.py snapshot --scope-root <root> --out <file>`.
   After the workers finish and before any shared write:
   `parallel_guard.py verify --scope-root <root> --before <file> --allow FEAT-001=<patterns> ...`.
   Exit 1 lists stray writes and collisions: reject those workers and rerun them; never
   keep or hand-edit their files. Put the snapshot file outside the scope root.
6. **Verify before trust.** Worker output is unverified until the guard, the skill's
   hash/coverage check and the lint gate pass for that item. A failing item goes back to
   its own worker (once), then to the user; passing siblings are kept.
7. **Smallest capable model** for workers. Use a low-cost model for mechanical, bounded
   writes; use a stronger model when the task needs cross-file reasoning. Choose from the
   host's available models; never assume a provider or hard-code a model ID. Keep independent
   reviewers at the session model unless the user selects another. Run maintenance and lint
   once at the end, not per worker.
8. **Workers never advance a station.** The batch finishes the local station; the lead then
   hands the whole batch off once by `handoff.md` (`flow: auto`: at once; `guided`: one plain
   yes covers the batch). A worker never transitions, approves or calls the next skill.

## Report

One line per item: station, condition, guard result, lint result, open questions. Name
anything unverified. Questions workers proposed are saved by the lead. The lead merges duplicates, ranks the rest
and asks the user at most five at once (`stop-and-ask.md`); the others stay saved as open
questions with options and a stated default and are asked in the next round.
