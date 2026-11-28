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
| in-development | In Progress; written by sw-forge while a task is `in-progress` |
| superseded | Won't Do |
| withdrawn | Won't Do |

## Task statuses

Every task carries `Status:` in `tasks/FEAT-NNN/FEAT-NNN.tasks.md`: `not-started` (the default when the
line is absent), `planned` (sw-forge wrote its detailed plan section), `in-progress`, `done`
(with an `Evidence:` line saying how it was proven) or `blocked` (with `Blocked because:`). A
withdrawn task stays as a `~~TASK-001-3~~` tombstone.

A story's condition follows its tasks: `in-development` while any task is `in-progress`, and
`done` only when every task is `done` **and** every acceptance criterion has evidence.
sw-forge is the only writer of these lines (`forge.py status` in its own scripts folder).

## Who sets each status

| Status | Set by |
| --- | --- |
| `draft` | sw-craft when it creates the story; sw-start's `return-spec` transition |
| `in-review` | sw-start's `submit-review` transition, after a passing review lint gate |
| `ready-to-publish` (accepted) | sw-craft only |
| `published` | sw-ship, after every remote operation succeeded |
| `ready-for-dev` | No skill writes it. It is recognised when a story already carries it (for example mirrored from Jira) and is treated like accepted for planning |
| `in-development`, `done` | sw-forge (`forge.py status`), from the tasks |
| `superseded`, `withdrawn` | An authorized withdrawal or replacement; the ID stays as a tombstone |

## Ownership

The manifest `status_map` is the mapping. sw-ship checks drift against it; the lint
capability checks status validity; only sw-craft moves a draft to `ready-to-publish`. A
status change never implies approval; approval is a hash-bound accept or named evidence
(`governance.md`).
