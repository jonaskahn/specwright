# Governance

One source of truth for how much ceremony a project wants. Other files point here instead of
restating a gate. The manifest holds the setting; the code computes the state, so switching
modes needs no migration.

```yaml
governance:
  signoff: optional   # optional (default) | required (the strict, formal rules)
  flow: guided        # guided (default): run through, one plain confirm per station | step
output:
  default: markdown   # jira or both only when Jira is configured or the user asks to push
```

Read it with `workspace.py governance get`, change it with
`workspace.py governance set signoff required`. `start.py` reports both values.

## Gates under each sign-off setting

| Gate | `optional` (default) | `required` |
| --- | --- | --- |
| Review | Lint and DoR pass, then the owner confirms in plain words. `review.py accept` writes `ready-to-publish` and `self \| accept \| sha256:<12> \| <date>`. | A configured approver's evidence (role, name, https URL, matching hash) through `review.py verify` and `promote`. |
| Formal sign-off | Allowed and shown as `signed-off`; never needed. | The only thing that counts. A self-accept reads as `needs-signoff`. |
| Active approval | A fresh accept line or a fresh verified sign-off. | A fresh verified sign-off only. |
| Content changes after approval | The line goes stale; one plain re-accept restores it. | Fresh evidence is needed again. |
| Accept a split | `record.py accept-split` may omit role, name and evidence; it records `decided_by: owner (self)` with `session` evidence. | An approver from the manifest and an https evidence URL. |
| Decisions and answers | The decider may be omitted (owner, session); a named one is checked only when approvers exist. | Approver from the manifest and a real evidence kind; `session` is refused. |
| Lint L-060 / L-061 | Warning. | Error. |
| Lint L-045 | Met by a fresh accept line or fresh sign-offs. | Fresh sign-offs for every approver role. |
| Setup | No approver question. | sw-start asks for approvers. |
| Plan | Needs an accepted story with a current approval. | Needs a fresh verified sign-off. |
| Publish | Needs an accepted story and a clean publish lint. A plan is not required, because tasks are never published. | Same, with a fresh verified sign-off. |

`ready-to-publish` is the stored status value, kept so no data migrates. Show it as
**accepted** in every message, status line and the console.

## Never relaxed

Kept in both modes: the three-way dry-run, identity checks, no remote deletes, no forced
transitions, a successful quality gate before any remote apply, and a fresh confirmation of
the exact plan shown in the current session. Only sw-publish writes to Jira or Confluence.
Imported text is never approval. A plain yes is not a formal sign-off under `required`, and it
is never remote permission unless it answers the exact dry-run just shown.

## Guided flow

`flow: guided` runs the stations in order: shape, spec, review (accept), plan. Publish is entered
only on an explicit request (`lifecycle.md`), never as a next step.

- After a station finishes with no blocker, show a short summary and ask
  **"Continue to <next station>? (Y/n)"**. A plain yes advances. For a local transition the agent
  passes the TRANSITION token itself after that yes; the user never types a token.
- Stop only on a blocker: a blocking question, a lint error, an ambiguous scope, a missing
  input or a publish step. Ask, and let the user decide.
- Save a non-blocking unknown as a question with its default applied (the command is in
  `stop-and-ask.md`), list it in the summary and keep going. An assumed question can still be
  answered later.
- `flow: step` keeps one stop per station and waits for the user to name the next one.

## Jira only when wanted

New workspaces deliver Markdown. There is no destination question in normal flow. When the user
says "push" or "publish": if Jira is configured, go to sw-publish; if not, say that Markdown
is already delivered and offer `workspace.py jira set --site <url> --project-key <KEY>` (read it back with `jira get`). A stored answer never
authorizes a write.

For the exact-plan confirmation, the user may reply "yes" to the dry-run just displayed. The
agent then passes `PUBLISH <scope>:FEAT-NNN <hash>` to `publish.py confirm --confirm`. The
confirmation stays fresh and bound to the plan hash; a changed plan needs a new yes.
