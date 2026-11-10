# status map

Feature statuses flow through the repository and map onto Jira statuses.

## Repository statuses

`draft`, `in-review`, `ready-to-publish`, `published`, `ready-for-dev`, `superseded`,
`withdrawn`.

## Default Jira mapping

| Repository     | Jira          |
|----------------|---------------|
| published      | To Do         |
| ready-for-dev  | Ready for Dev |
| in-development | In Progress   |
| superseded     | Won't Do      |
| withdrawn      | Won't Do      |

## Ownership

The manifest `status_map` is the mapping; Publish checks drift against it, `lint capability`
checks status validity, and only `sw-review` moves a draft to `ready-to-publish`.
A status change never implies approval; approval needs named evidence.
