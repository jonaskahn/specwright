# rtm contract

The traceability matrix has one owner per column; trace capability owns the rows and the
registry `Kind` column.

## Column owners

| Column      | Owner      |
|-------------|------------|
| BO          | sw-spec    |
| BR/NFR      | sw-spec    |
| Story draft | sw-spec    |
| Jira        | sw-publish |
| Jira status | sw-publish    |
| Sign-off    | sw-review  |
| Drift       | sw-publish    |
| Test ref    | qa         |

`scripts/trace.py set <id> --column <name> --as <skill>` refuses a column the skill does
not own, with exit 4. Row creation (`rebuild`) belongs to trace capability; every other skill
updates only its assigned column through trace capability.

## Registry columns

The ID registry holds external keys: `Jira key`, `Confluence id`, `Label`,
`Entity property`, `Last published draft hash`, `Last snapshot`, `State`. Column
ownership there is also enforced — trace capability owns `Kind`; sw-spec owns `Kind`/`State`;
sw-publish owns their key/snapshot/state cells.

## Qualified references

Use qualified IDs (`SCOPE:FEAT-NNN`) across projects. The matrix resolves against the
selected scope; a reference to another scope must be qualified or it reads as an orphan.
