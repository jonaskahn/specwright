# Governance

One source of truth for how much ceremony a project wants. Other files point here instead of
restating a gate. The manifest holds the setting; the code computes the state, so switching
modes needs no migration.

```yaml
governance:
  signoff: optional   # optional (default) | required (the strict, formal rules)
  flow: auto          # auto (default): hand off on its own, stop only for the user | guided | step
output:
  default: markdown   # jira or both only when Jira is configured or the user asks to push
```

Read it with `workspace.py governance get`, change it with
`workspace.py governance set signoff required`. `start.py` reports both values.

A separate manifest key, `checkpoint: push | commit | off` (default `push`), sets whether a skill
command's spec changes are committed and pushed (`checkpoint.md`). It is not a gate: it never
approves, advances a station or writes to Jira.

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
| Publish | Needs an accepted story and a clean publish lint. A plan is not required; the level published (epic, story, tasks) is the user's explicit choice. | Same, with a fresh verified sign-off. |

`ready-to-publish` is the stored status value, kept so no data migrates. Show it as
**accepted** everywhere (`status-map.md`).

## Never relaxed

Kept in both modes: the three-way dry-run, identity checks, no remote deletes, no forced
transitions, a successful quality gate before any remote apply, and a fresh confirmation of
the exact plan shown in the current session. Only sw-ship writes to Jira or Confluence.
Imported text is never approval. A plain yes is not a formal sign-off under `required`, and it
is never remote permission unless it answers the exact dry-run just shown.

## Flow: how the run goes from station to station

The stations run in order: shape, spec, review (accept), plan. Publish is entered only on an
explicit request (`lifecycle.md`), never as a next step. `handoff.md` is the procedure; the
answer comes from `_shared/scripts/handoff.py next`, the same in every skill and every state.

| `flow` | After a station finishes with no blocker |
| --- | --- |
| `auto` (default) | Hand off at once: load the next skill and run it in the same turn. No "continue?" question. |
| `guided` | Show a short summary and ask **"Continue to <next station>? (Y/n)"**; a plain yes advances. |
| `step` | Stop and wait for the user to name the next station. |

In every mode:

- Stop only on a human decision or a blocker: split acceptance, story acceptance or sign-off,
  a blocking question, a lint error after the one repair pass, an ambiguous scope, a missing
  input, an unknown state, or a publish step. Ask once, with everything gathered, and let the
  user decide. Under `auto` these are the only stops.
- Local transitions (`submit-review` after a passing review lint; the reviewed feature entering
  plan after an accept) are taken by the agent: it previews the TRANSITION token and passes it
  itself. Under `guided` it does so after the plain yes. The user never types a token. A
  transition is never approval.
- A batch accept (sw-craft) is valid only as the answer to the table just shown: each named
  feature is bound to the hash shown, and a draft that changed since is excluded. Moving a batch
  on to the next station covers the batch, never an approval.
- Save unanswered decisions as open questions (`stop-and-ask.md`); never apply defaults or
  manufacture consent. Work depending on the answer waits; independent work continues.
- The user can stop the chain at any time ("pause", "only spec FEAT-004", "stop after review")
  or change the mode for one run (`handoff.py next --flow step`).

Change the stored mode with `workspace.py governance set flow auto|guided|step`. A workspace set
up before kit 0.7.0 stored `flow: guided`; set `auto` to get the hand-off without questions.

## Jira only when wanted

New workspaces deliver Markdown. There is no destination question in normal flow. When the user
says "push" or "publish": if Jira is configured, go to sw-ship; if not, say that Markdown
is already delivered and offer `workspace.py jira set --site <url> --project-key <KEY>` (read it back with `jira get`). A stored answer never
authorizes a write.

For the exact-plan confirmation, the user may reply "yes" to the dry-run just displayed. The
agent then passes `PUBLISH <scope>:FEAT-NNN <hash>` to `publish.py confirm --confirm`. The
confirmation stays fresh and bound to the plan hash; a changed plan needs a new yes.
