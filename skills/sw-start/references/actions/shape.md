# Shape action

Shapes an early proposal into a problem-led idea brief and an INVEST feature split.
This action replaces the old sw-shape-idea name.

## Steps

1. Resolve scope before writing. With pasted material, synthesize a provisional brief
   separating sourced facts, proposals and unknowns; with a sparse idea, ask only the
   highest-impact unanswered questions.
2. Read references/domain/idea-method.md and fill assets/idea-brief.md. Include actor
   context, the observed problem, the smallest outcome, at least three non-goals with
   reasons, falsifiable assumptions and risks linked to draft RISK records.
3. Run scripts/leakage.py with the brief path. Exit 0 is clean, 1 means rewrite the
   reported passages, 2 means repair invocation or input. Never weaken the word list
   to pass.
4. Propose feature slices with references/domain/invest.md. Give each proposed feature
   a verb-first title, one principal actor and a valuable outcome; record
   I/N/V/E/S/T with a one-line reason per letter. Reserve FEAT IDs only after explicit
   acceptance; record a DEC-NNN with role, name, date, affected IDs and evidence URL.
5. Render a picture only when it resolves a concrete ambiguity; do not invent accepted
   requirements.

## Boundaries

- A widget is not a problem, and naming an API is not a business outcome.
- A clean word scan does not prove absence of design leakage or INVEST quality.
- Neither an unanswered default nor a confident synthesis can authorize a split.
