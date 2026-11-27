# RTM contract

The traceability matrix has one owner per column. The trace capability owns rows.
Enforced in kitlib/rtm.py.

## RTM columns

| Column | Owner |
| --- | --- |
| BO | sw-craft |
| BR/NFR | sw-craft |
| Story draft | sw-craft |
| Jira | sw-ship |
| Jira status | sw-ship |
| Sign-off | sw-craft |
| Drift | sw-ship |
| Test ref | qa |

`_shared/scripts/trace.py set <id> --column <name> --as <skill>` refuses a column the skill does
not own (exit 4). Row creation (`rebuild`) belongs to the trace capability; every other
skill updates only its own columns through it.

## Registry columns

The ID registry holds external keys: `Kind`, `Jira key`, `Confluence id`, `Label`,
`Entity property`, `Last published draft hash`, `Last snapshot`, `State`, and for
reserved items that have no file yet `Title`, `Aliases` (legacy IDs, `|` separated) and
`Source ref` (the remote page or tracker key an imported snapshot came from).
`Jira key` and `Confluence id` mean "published as"; an import never writes them. A
registry written by an older release is widened when read and rewritten by the workspace
upgrade.

| Writer | May set |
| --- | --- |
| trace capability | Kind |
| sw-craft | Kind, State |
| sw-craft | Kind, State, Title, Aliases |
| sw-craft | Kind, State, Last snapshot, Source ref |
| sw-ship | Jira key, Confluence id, Label, Entity property, Last published draft hash, Last snapshot, State |

## Qualified references

Use `SCOPE:FEAT-NNN` across projects. The matrix resolves against the selected scope; an
unqualified reference to another scope reads as an orphan.
