# Hand-off between stations

How one station passes the work to the next. Under `flow: auto` (the default) the hand-off is
not a question: when a station finishes cleanly, the agent loads the next skill and starts it
in the same turn. The run stops only where a person has something to decide or supply.
`governance.md` holds the setting; this file is the procedure every skill follows.

## Contents

- The rule
- When the run stops
- Procedure at the end of every station
- Entering at any state
- The user stays in control
- What a hand-off never does
- Example run

## The rule

**Continue on your own; stop only for a decision, a missing input or a blocker.**

A finished station is not a reason to pause. Lint, DoR and the task check are the machine
gates between stations, and they run automatically; the human gates are the decisions only a
person can make. Each stop asks one batch of questions, never a bare "continue?".

| Just finished | No blocker → next, automatically | Human gate inside the next step |
| --- | --- | --- |
| sw-craft | Re-route with sw-start (shape for a new idea, spec for clear features) | Proposed impacts on accepted or published stories wait for a decision |
| sw-craft writing | — | Owner accepts or revises the split (`accept-split`) |
| Split accepted | sw-craft for every reserved feature (parallel batch) | — |
| sw-craft | `submit-review` (agent passes the token itself), then sw-craft | Independent reviewers debate first (no stop); then the owner finalizes the review pack (`signoff: optional`), or sign-off evidence (`required`) |
| Accept recorded | Done for the BA role: the run stops and lists the accepted stories | — |
| The user says forge | sw-forge for the named feature | The code is written elsewhere, from the prompts |
| sw-forge, check passes | Done: Markdown delivery | — |
| Any station, publish | Never automatic | sw-ship dry-run and a fresh yes to it |

`submit-review` moves a draft to review; it is not approval. The transition refuses on its own
while a blocking question is open or the review lint fails, so the agent may pass the token
without asking. Approval stays human: only sw-craft records it, from the owner's answer to
the table it just showed.

## The role boundary

sw-craft ends at the finalize. It never loads sw-forge by itself: the BA may be a different
person from the Dev, and the Dev may write code in another repository. When the last story of
a run is accepted, the hand-off is `done` with one line — "Say **forge** to plan FEAT-001" —
not a `continue` into sw-forge. A user who plays both roles says forge, and one confirm
switches over.

## When the run stops

Stop, say why in one line, and ask (at most five questions, `stop-and-ask.md`) when:

1. **A human decision is due**: split acceptance, story acceptance or sign-off, a conflict
   between sources, a scope choice that changes boundaries, a reopened slice.
2. **An input is missing**: no source for a needed rule, an unanswered blocking question,
   an ambiguous write scope, sign-off evidence under `required`.
3. **A check stays red after one repair pass**: lint error, DoR gap, failing task check
   (`completion.md`, Repair). Never weaken a rule to keep moving.
4. **The state is unknown**: conflicting decisions, an incomplete transaction, an unknown
   station. Inspect; never guess.
5. **The next step is outside the local pipeline**: publication, a runtime install, a workspace
   upgrade, rewinding published text. These keep their own explicit confirmations.
6. **The user asked to stop**: "only spec FEAT-004", "stop after review", "pause". Pass
   `--until <station>` to `handoff.py` and stop there.
7. **The pipeline is finished**: every item is complete in plan. Report the delivery; do not
   offer publication.

An unknown never authorizes a guessed answer. Save it as open (`stop-and-ask.md`); hold any
work depending on it and continue independent items. A non-blocking question changes no rule.

## Procedure at the end of every station

1. Finish the station's own work.
2. Run one command; it does maintenance, checks, checkpoint and the hand-off decision:

   ```sh
   _shared/scripts/finish.py --skill <this skill> --subject "<what changed>" --cwd <project> [--item <key>]... [--until <station>]
   ```

   Pass `--item` when the user named items (only those move; an epic moves its members). Omit it
   for "continue" or a bare command (the whole scope, station by station). The decision alone,
   without maintenance: `_shared/scripts/handoff.py next --cwd <project> --done <skill>`.
3. Act on `handoff.mode`:
   - `continue`: print `say` as one line (for example `→ sw-craft for REF:FEAT-001, REF:FEAT-002`),
     apply each entry in `transitions` with `../sw-start/scripts/transition.py <action> --item <key>`
     (preview, then `--confirm` with the token it printed), then read `../<next_skill>/SKILL.md`
     and run it for `items` at once. If that skill is not installed, name it and stop.
   - `repair`: the lint gate is blocked. Fix the findings once, rerun finish.py with `--repaired`.
   - `confirm` (`flow: guided`): print the short summary and `ask`; a plain yes continues.
   - `stop`: print the summary, then the `reason` and the questions for every entry in `waiting`
     together, in one batch, with 2–3 ready replies.
   - `done`: report the delivery (story, plan, tasks, agent prompts) and stop.
4. After the next skill finishes, repeat from step 1. The chain ends only at a stop or done.

A transition that refuses (blocking question, lint) turns that item into a stop with the
refusal as the reason; the rest of the batch goes on.

Order inside one run: `handoff.py` takes the work that needs no answer first (spec, then plan)
and the stations that end in a question last (shape, then review), so the user is asked once,
at the end, with everything gathered. After the answer, the chain resumes from the board.

Write one short line per hand-off, not a report per station. The full summary (what was made,
open questions, checkpoint lines) comes once, at the stop or at done.

## Entering at any state

The board, not the conversation, says where work stands, so a run can start anywhere:

- **A skill invoked by name** (`/sw-craft FEAT-004`) checks its own prerequisites, does its
  work, then hands off by this procedure like any other station.
- **"continue", "go on", "next", "resume"** with no item: run `handoff.py next` (no `--done`)
  and start the skill it names for the whole scope. sw-start does this when it is loaded.
- **A named item mid-pipeline** ("resume FEAT-004"): `handoff.py next --item FEAT-004`; an
  unfinished station resumes without repeating its entry.
- **A new chat**: same as "continue". Nothing from an earlier chat is needed; a remembered yes
  never counts as an approval.
- **After a stop is answered**: record the answer (records, accept, split), then run
  `handoff.py next` again and keep going.

When the session is near its context or time limit, finish the current station, run its
checkpoint, and stop with "Say continue to pick up at <next skill>". The files carry the state.

## The user stays in control

- Any message from the user interrupts the chain; answer it first, then resume from the board.
- At any state offer evidence, correction, scope change or leaving a decision unresolved when
  an answer is needed. Changed source evidence invalidates the related inferred conclusion,
  not unrelated approvals; show the change and ask before using a replacement decision.
- "pause", "stop here", "only <station>" end the chain at that point (`--until`).
- "one at a time" or "step mode" for this run: pass `--flow step`; to keep it, run
  `workspace.py governance set flow step` (or `guided` for one confirm per station).
- Siblings move only when the run covers the whole scope ("continue", a bare command). A named
  item moves alone.

## What a hand-off never does

- Approve, sign off or accept a split. Those come from the user's answer to what was shown.
- Publish, write to Jira or Confluence, or enter sw-ship. A stored Jira preference is no
  request.
- Install a runtime or upgrade a workspace without the exact command confirmed this session.
- Skip lint, DoR or the task check, or retry past the one repair pass.
- Loop: when the same skill would run again on the same items with nothing changed, `handoff.py`
  answers `stop` with "no progress". Inspect and report instead of retrying.

## Example run

User: "spec the refunds epic". The split is already accepted with three reserved features.

```text
→ sw-craft for REF:FEAT-001, REF:FEAT-002, REF:FEAT-003      (parallel, one worker each)
  2 open non-blocking questions saved (Q-004, Q-005); FEAT-002 waits on blocking Q-003
→ sw-craft for REF:FEAT-001, REF:FEAT-003                  (submitting drafts first; not approval)

| Feature  | Verdict | Hash         | Blocks |
| FEAT-001 | pass    | sha256:1a2b… |        |
| FEAT-003 | pass    | sha256:9f8e… |        |

Q1 [blocking] Which refund window applies to FEAT-002? Checked SRC-0001, SRC-0002.
   A) 14 days -> the policy source needs amendment.  B) 30 days -> refund tiers change.
   Default if unanswered: Q-003 stays open; FEAT-002 stays in spec.
Accept FEAT-001, FEAT-003 (hashes shown)? Answer yes for all listed, or name a subset.
```

User: "yes, and B". The agent records the answer to Q-003 and both accepts, runs
`handoff.py next`, and goes on without asking:

```text
→ sw-craft for REF:FEAT-002     (applying the answer to Q-003)
→ sw-forge for REF:FEAT-001, REF:FEAT-003
→ sw-craft for REF:FEAT-002   (submitting the draft first; not approval)
Accept FEAT-002 (sha256:77c1…)?
```

Two stops in the whole run, each one a real decision. After the last yes, sw-forge runs for
FEAT-002 and the run ends with the Markdown delivery.
