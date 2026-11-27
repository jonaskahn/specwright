# Candidate extraction contract

Each worker writes exactly one file, `01-analysis/candidates/CAND-NNN--<area>.md`, created for it by
`scripts/candidates.py assign`. The script also writes `assignment.tsv`, the record of which worker
reads which snapshot. Do not create, rename or edit any other file.

## File shape

Front matter is fixed by the skeleton: `id`, `type: candidates`, `covers` (your snapshots), `count`,
`status`. Set `count` to the number of table rows when you finish. The body has these sections:

- `## Covered`: your snapshots, as listed. Read only those.
- `## Candidates`: one table, columns exactly `# | Kind | Topic | Claim | Citation | Status | Note`.

## Rows

| Column | Rule |
| --- | --- |
| `#` | 1, 2, 3 ... in order, no gaps. The item key is `CAND-NNN.<#>`. |
| Kind | `rule`, `number`, `actor`, `term`, `constraint` or `other`. |
| Topic | A short, stable name for what the claim is about. The same topic across workers is how conflicts are found, so reuse wording. |
| Claim | A summary in at most 40 words. Never paste source text; exact text is copied by program (`cite.py quote`). |
| Citation | `SRC-0001:L12-L14#a1b2`, one or more, all from your own snapshots. Get the hash from `cite.py stamp`. |
| Status | `raw`. Only the lead changes it (`accepted`, `rejected`, `merged`). |
| Note | Empty, or the `CAND-NNN.n` a merged claim joined. |

The body stays under 2,500 words. A claim you cannot cite does not go in the table.

## Checks and trust

`scripts/candidates.py check` confirms every snapshot was assigned once, each worker's `covers` matches
the assignment, every citation resolves with its hash and names only your snapshots, numbering and
`count` agree, and every claim is short. Until it passes, treat every claim as unverified. A passing
check proves the citations exist, not that the claim is right: a named person reviews accepted claims.

`scripts/candidates.py conflicts` lists claims on the same topic that differ, with both citations,
before any question is raised. Raise each consequential one with
`record.py q new --raised-from CAND-001.3 --raised-from CAND-002.1`.
