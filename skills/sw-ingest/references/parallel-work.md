# Parallel extraction

Use this when the sources are larger than one reading session, for example a wiki of dozens of
pages. The general fan-out rules (one writer per file, lead-owned shared state, the write guard,
verify before trust, smallest capable model, at most 8 workers at a time) are in
`_shared/references/parallel-writers.md`. This page adds only what ingest changes.

1. **Partition.** Import first (`bulk_import.py`), then run `candidates.py assign`. It groups
   snapshots by the top page they hang under (else the first label, else their own area) and packs
   each group into workers of about 18,000 words. The assignment is saved, so coverage can be
   checked and a later import is assigned by running it again.
2. **Brief each worker** with only its candidates file, its snapshots, the contract in
   `references/candidate-contract.md` and the untrusted-content rule. Give it no other snapshot,
   no registry and no records. Secrets and personal data are already out of the snapshots
   (redacted copies), so a worker never receives raw originals.
3. **Guard the writes.** Snapshot before launching and verify afterwards as the shared rules say,
   with one allow-list per worker: `CAND-001=01-analysis/candidates/CAND-001--*`. A worker writes its
   own candidates file and nothing else; only the lead changes a status or creates a question.
4. **Reconcile.** Run `candidates.py check`: every snapshot read once, every citation resolves,
   counts add up. Fix a worker's file by sending it back, not by editing it. Worker output stays
   unverified until the guard and this check pass, and its accuracy until a named person reviews
   it. Report what was verified and what was not.
5. **Conflicts.** Run `candidates.py conflicts` before any question; ask for each consequential
   one (`stop-and-ask.md`) and record the decision through `record.py`.
