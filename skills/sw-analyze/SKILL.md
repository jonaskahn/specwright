---
name: sw-analyze
description: Analyses an existing system or feature, wherever it lives (code in this repo or beside it, tests, docs, Jira, another system) and compares what it should do with what it does today, criterion by criterion, as a gap table (done, partial, missing, divergent, unknown). Adopts a project mid-life: detects code roots, writes a light inventory of candidate features, and recovers a feature's current behaviour with code citations. Use when asked to analyse, understand, audit or take over an existing feature or codebase, to find what is missing in a partly built feature, before changing or fixing existing behaviour, or to check whether a change is really shipped. Do NOT use to write stories (use sw-spec) or to import documents (use sw-ingest).
---

# sw-analyze

Compare intended with actual behaviour. Code and documents weigh the same. Read code; never write it.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`01-analysis/as-is/inventory.md`, `01-analysis/as-is/<target>.analysis.md`, `code_roots` in the
manifest (after a yes), Q records via `_shared/scripts/record.py`.

## Steps

1. `scripts/analyze.py roots`. Detected, unregistered roots → list them, ask once, then
   `roots --add <path> ...`. No code anywhere → continue; the actual side is empty.
2. No `inventory.md`, or the user asks for an overview → `scripts/analyze.py inventory`. Show the
   top candidates (≤ 10 lines). The user picks; with a named feature skip the choice.
3. Intended sources not yet imported (docs, Jira, Confluence, another system) → sw-ingest them
   first; cite `SRC-NNNN:Lnn#hash`.
4. `scripts/analyze.py area <keywords>` → read only the listed files, docs first, then code and
   tests (`references/method.md`).
5. `scripts/analyze.py new <FEAT-NNN|slug>`; fill one Criteria row per observable behaviour.
   Cite code with `scripts/analyze.py cite <root>/<path> --lines A-B`. Code-only behaviour:
   Intended = `observed`. Sources disagree → `divergent` + a Conflicts line quoting both:
   `Q-NNN` (`record.py q new --affects FEAT-NNN`) when the feature exists, else `ASK-n`;
   sw-spec turns ASK-n into Q records once the feature has an ID.
6. `finish.py --skill sw-analyze --item <target>` checks the table. Rows done + high confidence
   with a test or two code cites are accepted on their own; every other row is asked in one batch.
7. Before shipping a change: `scripts/analyze.py new FEAT-NNN --verify` (one row per AC of the
   change), cite the code, finish with `--item FEAT-NNN.verify`. All rows done → sw-spec ships
   and merges; any gap → report it; the owner fixes the code or ships with a stated reason.
8. After the owner confirmed the asked rows: `scripts/analyze.py confirm <target>`.

## Stop when

Registering code roots; choosing a candidate; rows that need confirmation; a divergence (code
wrong or spec wrong is the owner's call); a source that cannot be read.

## Finish

Run `_shared/scripts/finish.py --skill sw-analyze --subject "<target> analysis" --cwd <project>
--item <target>`. `continue` → sw-spec with the `recommend` text (version 1, completion change,
fix or new story); `repair` → fix the table once, rerun with `--repaired`; `stop` → ask `waiting`.

## Load only when

| Need | File |
| --- | --- |
| How to read code for behaviour, statuses, confidence | references/method.md |
| Shapes and what sw-spec writes next | references/method.md (Shapes) |
| Importing intended sources | ../sw-ingest/SKILL.md |
| A step above is unclear or a script errors | references/procedure.md |
