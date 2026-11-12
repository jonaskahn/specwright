# Parallel writers

Use this when two or more independent items (features) wait at the same station in one
scope and the host can run sub-agents. It gives speed without shared-write races.

## When

- Fan out for 2+ items: reserved features to specify, accepted features to plan, submitted
  features to prepare for review. For review the workers only check; accepts stay with the lead
  (sw-review "Several features").
- Stay serial for one item, an amendment of published text (CR and snapshot gate), a scope
  that is ambiguous, or a host without sub-agents. Say which, in one line.
- One worker per item. Run up to 8 at a time; the rest follow in the next wave.
- Workers on items that share a decision wait until the lead has recorded it, so no two
  workers invent different rules.

## Rules

1. **One writer per file.** A worker owns its item's files only (the skill names them).
   It never writes records, registry rows, RTM, graph, `_meta/data/`, status, snapshots,
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
7. **Smallest capable model** for workers. Run maintenance and lint once at the end, not
   per worker.
8. **Never advance a station.** The batch finishes the local station; the next transition
   still needs the user's confirmation. Under `flow: guided` one plain yes covers the batch.

## Report

One line per item: station, condition, guard result, lint result, open questions. Name
anything unverified. Questions workers proposed are saved by the lead. The lead merges duplicates, ranks the rest
and asks the user at most five at once (`stop-and-ask.md`); the others stay saved as open
questions with options and a stated default and are asked in the next round.
