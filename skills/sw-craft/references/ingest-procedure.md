# sw-craft — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

1. Resolve scope before any write; in a program workspace ask when no explicit scope or
   project path selects it. Run one import at a time per scope. Get consent to retain
   known sensitive originals before importing them.
2. Convert each file: run scripts/to_md.py <file> --out <project>/00-inbox/ (add
   --scope REF in program mode); routes and limits are in references/router.md. Read
   its JSON and stderr. Exit 0 complete or duplicate (cite the existing SRC; do not
   allocate another), 2 bad input or converter failure, 3 unsafe input or consent
   needed, 4 degraded snapshot (not usable evidence). Give each page its name with
   --title, --alias, --remote-id, --remote-url, --tracker-key and --source-parent. A
   page of headings and links is flagged `content_class: index-only`: it is a map, not
   evidence. For many files run scripts/bulk_import.py --batch-id <id> (--dry-run
   first): it imports parents first, writes a manifest with expected and received
   counts, and imports every item in sub-batches of --batch-size (default limits.batch_size, else 50),
   with no total cap. Exit 5 means the
   received count differs from the expected one: never use that batch as whole.
3. Scan each snapshot: run scripts/secrets_scan.py <snapshot>; policy in
   references/pii-policy.md. Exit 1 (secrets) blocks hand-off: redact a copy with
   --redact --out (exit 0 once the copy scans clean), then ingest the copy with
   --redacted-from <sha256 of the original>. Keep originals restricted and untracked.
   --retain-sensitive-raw only records explicit user consent; never infer it. A sample
   value inside a policy text counts as a documented example only through a named,
   evidenced row in .metadata/scan-decisions.tsv (--decisions); never for a secret.
4. Remote evidence, in this order: a user-supplied export; the session read tools
   (jira-read, jira-search, wiki-read; definitions in
   `_shared/references/capabilities/remote.md`), naming the providing tool before the first call;
   for a wiki page tree, scripts/wiki_pull.py (read-only; exit 4 means the pull is incomplete,
   never import it as whole), then bulk_import.py on its list; otherwise ask for pasted data and
   mark unread fields UNKNOWN. Never improvise credentials. Pass remote version and URL
   through the to_md.py overrides. This skill never needs jira-write. If a snapshot has
   the right bytes but wrong provenance, run scripts/provenance.py amend (who and why
   required); never re-import to fix a header.
5. Many snapshots: split the reading with references/parallel-work.md and
   scripts/candidates.py (assign, check, conflicts); workers follow
   references/candidate-contract.md. Extract candidates and detect conflicts per
   references/extraction-checklist.md. Cite
   SRC id and line for every numeric claim. For each consequential conflict, write a Q
   record (`_shared/scripts/record.py q new`, quoting both sources with
   `--raised-from SRC-0001:L12-L14#hash`) with options and consequences; do not pick a
   winner.
6. Present draft STK, BO, BR, NFR, vocabulary and uncertainty candidates. Create cards
   only after acceptance. Keep unknowns explicit; never invent upstream links for legacy
   Jira material.
7. Associate evidence with features: query the fresh graph for the named flow. Only an
   explicit user target or an established mapping creates an association; lexical
   matches, even a single one, are suggestions. Several features may be affected.
8. Changed logic: run scripts/impact.py --source --item --source-quote --claim-quote to
   save an idempotent proposed CR. Both quotes must exist verbatim. This approves
   nothing, edits no requirement and increments no revision.

## Consumer check

Can the next analyst cite every number to the correct SRC and version? Raw bytes match
SHA-256, snapshots have no unhandled secrets, degraded or visually uncertain content is
not treated as settled evidence.

## Stop and ask

Questions follow `_shared/references/stop-and-ask.md`. Stop on encrypted input, oversized material, unverified page counts, missing scope,
sensitive-retention decisions or failed conversion. For a conflict ask which source
governs, the consequence of each option and who decides. Keep the Q open until
decision evidence supports a linked DEC record.

## Gotchas

- A hash proves byte identity, not correctness or authority. Same bytes = one snapshot; changed bytes = new SRC.
- PDF page checks need pdfinfo. A missing tool means degraded provenance, never fabricated prose.
- OCR misreads Vietnamese accents, dates, money and columns; check the original visually before extracting them.
- A ZIP listing is never permission to extract or open members.
- Legacy Office needs a reviewed macro-free export; multi-page TIFF waits for a verified page count.
- Writes are atomic per file, not per batch. If storage fails after the raw copy, reconcile original and registry before retrying.
- Secret scans are heuristics, not proof that opaque originals are safe.
- Never rewrite an immutable snapshot to add associations.
