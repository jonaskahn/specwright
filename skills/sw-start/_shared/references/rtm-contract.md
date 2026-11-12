# RTM contract

The traceability matrix has one owner per column. The trace capability owns rows.
Enforced in kitlib/rtm.py.

## RTM columns

| Column | Owner |
| --- | --- |
| BO | sw-spec |
| BR/NFR | sw-spec |
| Story draft | sw-spec |
| Jira | sw-publish |
| Jira status | sw-publish |
| Sign-off | sw-review |
| Drift | sw-publish |
| Test ref | qa |

`scripts/trace.py set <id> --column <name> --as <skill>` refuses a column the skill does
not own (exit 4). Row creation (`rebuild`) belongs to the trace capability; every other
skill updates only its own columns through it.

## Registry columns

The ID registry holds external keys: `Kind`, `Jira key`, `Confluence id`, `Label`,
`Entity property`, `Last published draft hash`, `Last snapshot`, `State`.

| Writer | May set |
| --- | --- |
| trace capability | Kind |
| sw-spec | Kind, State |
| sw-publish | Jira key, Confluence id, Label, Entity property, Last published draft hash, Last snapshot, State |

## Qualified references

Use `SCOPE:FEAT-NNN` across projects. The matrix resolves against the selected scope; an
unqualified reference to another scope reads as an orphan.
