# Intake, read-back and suggested replies

## First run (no workspace)
`start.py` returns `surface` and `intake`. Read the surface before asking. The current user
message is the change when it names the work; do not ask them to type it again. Ask at most
the questions the message and the surface left open, in one message, with options and a
default. Defaults are recommendations only.

1. Starting point: only when the message does not already name the change. An empty surface
   (no code, no docs, no README) offers the conversation, documents to import, or a register.
   It does not offer discover-docs or an existing system. A surface with files names them
   (README, `docs/`, a code marker) and may offer a scan. `context_intake` uses the same
   glance. No document-body scan without consent.
2. How far: spec / review / plan → pass as `--until spec|review|plan` to every `finish.py` call
   of this run. Skip when the message already says how far. Default recommendation: plan
   (stories, accepts, tasks, agent prompts).
3. Stack: detected layers → lock as detected / edit first / no lock. No code → name it now /
   decide at plan time / no lock. Skip when the message already chose.

With an ask-user tool, use tappable options and consequences. Never a free-text-only question.
Unanswered → leave unresolved; do not initialize using guessed answers or run the scan.
Continue only independent work, including shaping a change the user already described.

## Read-back
Before a run that writes more than one file, print one line:
`I will: shape the refund idea → spec ~3 features → stop at review for your accept.`
This restates explicit choices, never invents missing ones. The user may correct it at any state.

## Questions at a stop
- Lead with the blocking ones. Each: options, consequence per option, default.
- End with 2–3 ready replies the user can send as-is, e.g.
  `yes, all` · `accept FEAT-001 only` · `Q1: B`.

## "help" / "what can you do"
Print `start.py --brief`. Then one line: the next step from `handoff.say`.
