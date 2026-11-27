# Query cookbook

Every command accepts --cwd, --scope, --format text|json and --strict. Lists accept --limit (default 20, at most 200)
and --offset.

| Question                                  | Command                                                      |
|-------------------------------------------|--------------------------------------------------------------|
| Where do I start?                         | map, then map --epic EPIC-001                                |
| What is FEAT-001 and what links to it?    | show FEAT-001                                                |
| What is the item the business calls LEG-100? | show LEG-100 (any alias, remote ID, URL or title fragment) |
| Which items mention "refund window"?      | find "refund window" (searches ID, title and aliases)        |
| What does BR-001 govern?                  | neighbors BR-001 --dir in --rel governed_by                  |
| Which epic does AC-001-2 belong to?       | up AC-001-2                                                  |
| What sits under EPIC-001?                 | down EPIC-001 --depth 3                                      |
| How are TASK-001-1 and BO-001 connected?  | path TASK-001-1 BO-001                                       |
| What does changing BR-001 reach?          | impact BR-001 (also accepts a Jira key)                      |
| Which features are ready to publish?      | find --kind feat --status ready-to-publish                   |
| What assets support FEAT-001?             | neighbors FEAT-001 --dir in --rel supports                   |
| Which spec items use ASSET-001?           | neighbors ASSET-001 --dir out --rel supports                 |
| What should an agent read for TASK-001-1? | context TASK-001-1, add --with-text --budget 4000 for slices |
| Is the graph current and sound?           | check                                                        |

Per-item resume uses `board --item REF:FEAT-001 --format json`; an epic target
selects its feature slice. `board --station spec` filters stations. This query requires
a fresh compatible graph and returns items separately from rendered lines. A status
ready-to-publish is not proof that plan/task checks or remote-write gates pass.

Output reading:

- First line: graph: fresh, stale or missing.
- Each link shows [class/resolution] and file:line.
- A +N more line gives the next --offset.
- Exit 3 lists candidates when a name is ambiguous or unknown; it never picks one. Qualify an ID, for example
  REF:FEAT-001, or use a more specific name. `show` also reads the crosswalk row, parent and links from _meta/.
