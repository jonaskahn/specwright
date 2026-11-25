---
name: sw-ingest
description: Converts incoming business sources into hash-stamped Markdown snapshots, preserves original bytes, screens sensitive content, and identifies candidate facts and contradictions. Use when importing policy files, adding meeting notes or PO emails as evidence, or saving Jira issue JSON as background. Do NOT use for drafting stories or acceptance criteria (use sw-spec).
---

# sw-ingest

Import sources as immutable, cited Markdown snapshots. Approve nothing; edit no requirement.

Rules: `_shared/references/kernel.md` (read once per session). Artifacts follow
`_shared/references/agent-style.md`.

## Writes

`00-inbox/` snapshots and raw copies, `records/` Q and proposed CR (via scripts), source registry.

## Steps

1. Resolve scope. One import at a time per scope. Ask consent before keeping sensitive originals.
2. Convert: `scripts/to_md.py <file> --out <project>/00-inbox/` (exit 0 ok or duplicate, 2 bad
   input, 3 unsafe or consent needed, 4 degraded: not evidence). Many files:
   `scripts/bulk_import.py --batch-id <id> --dry-run`, then run; exit 5 = count mismatch.
3. Scan: `scripts/secrets_scan.py <snapshot>`. Exit 1 → redact a copy (`--redact --out`), ingest
   the copy with `--redacted-from <sha256>`.
4. Remote: user export first; else session read tools (name the tool first); wiki trees via
   `scripts/wiki_pull.py` (exit 4 = incomplete). Never improvise credentials.
5. Extract candidates and conflicts (`references/extraction-checklist.md`). Conflict → Q record
   quoting both sources (`record.py q new --raised-from SRC-…`). Never pick a winner.
6. Present draft STK/BO/BR/NFR candidates; create cards only after acceptance.
7. Changed logic in a story → `scripts/impact.py` saves a proposed CR. No requirement edit.

## Stop when

Encrypted or oversized input, unverified page count, missing scope, sensitive retention,
failed conversion, a conflict needing a governing source.

## Finish

Run `_shared/scripts/finish.py --skill sw-ingest --subject "<SRC ids> ingested" --cwd <project>` (add `--item` per named
item, `--until <station>` if the user set a limit). Act on `handoff.mode`: `continue` →
print `say`, apply `transitions`, load `../<next_skill>/SKILL.md` now; `repair` → fix lint once,
rerun with `--repaired`; `confirm` → ask once; `stop` → ask what `waiting` needs; `done` → report.

## Load only when

| Need | File |
| --- | --- |
| Converter routes, limits, exit codes | references/router.md |
| Candidates, conflicts | references/extraction-checklist.md |
| Many snapshots, workers | references/parallel-work.md; references/candidate-contract.md |
| Secrets or personal data | references/pii-policy.md |
| Mockups, links, images in a batch | _shared/references/capabilities/assets.md |
| Remote read tools | _shared/references/capabilities/remote.md |
| A step above is unclear or a script errors | references/procedure.md |
