# Status map

## Repository feature statuses

`draft`, `in-review`, `ready-to-publish`, `published`, `ready-for-dev`, `superseded`, `withdrawn`.

`ready-to-publish` is the stored value; readers see it as **accepted**. The approval reads
`accepted` (the owner's accept), `signed-off` (a formal sign-off) or `needs-signoff` (only an
accept exists while sign-off is required).

## Default Jira mapping

| Status | Jira |
| --- | --- |
| published | To Do |
| ready-for-dev | Ready for Dev |
| in-development | In Progress (Jira side only; not a repository status) |
| superseded | Won't Do |
| withdrawn | Won't Do |

## Ownership

The manifest `status_map` is the mapping. sw-publish checks drift against it; the lint
capability checks status validity; only sw-review moves a draft to `ready-to-publish`. A
status change never implies approval; approval is a hash-bound accept or named evidence
(`governance.md`).
