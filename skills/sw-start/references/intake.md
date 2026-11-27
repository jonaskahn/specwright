# Intake, read-back and suggested replies

## First run (no workspace)
`start.py` returns `intake`: at most three questions with options and a default, prefilled
from what it detected. Ask them in one message. Never ask what the scan answered.

1. Starting point: idea / documents / register or Jira → routes to sw-craft, sw-craft, or the
   existing-baseline flow.
2. How far: spec / review / plan → pass as `--until spec|review|plan` to every `finish.py` call
   of this run. Default: plan (stories, accepts, tasks, agent prompts).
3. Stack: detected layers → lock as detected / edit first / no lock. No code → name it now /
   decide at plan time / no lock.

With an ask-user tool, use tappable options. Unanswered → apply the default and say so.

## Read-back
Before a run that writes more than one file, print one line:
`I will: shape the refund idea → spec ~3 features → stop at review for your accept.`
The user may correct it; otherwise continue without waiting.

## Questions at a stop
- Lead with the blocking ones. Each: options, consequence per option, default.
- End with 2–3 ready replies the user can send as-is, e.g.
  `yes, all` · `accept FEAT-001 only` · `Q1: B`.

## "help" / "what can you do"
Print `start.py --brief`. Then one line: the next step from `handoff.say`.
