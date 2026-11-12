# Parallel extraction

Use this when the sources are larger than one reading session, for example a wiki of dozens of pages.

1. **Partition.** Import first (`bulk_import.py`), then run `candidates.py assign`. It groups snapshots by the
   top page they hang under (else the first label, else their own area) and packs each group into workers of
   about 18,000 words. The assignment is saved, so coverage can be checked and a later import is assigned
   by running it again.
2. **Brief each worker** with only: its file path, its snapshots, `references/candidate-contract.md`. Give
   it no other snapshot, no registry and no records. Secrets and personal data are already out of the
   snapshots (redacted copies), so a worker never receives raw originals.
3. **One writer per file.** A worker writes its own candidates file and nothing else. It never writes a
   record, a registry row, a snapshot or another worker's file. The lead is the only one who changes a
   status and the only one who creates a question.
4. **Exactness by program.** A worker summarizes and classifies. Quoted text, citation hashes and
   line numbers come from `cite.py quote` and `cite.py stamp`; a worker never retypes source text.
5. **Reconcile.** Run `candidates.py check`: every snapshot read once, every citation resolves, counts add
   up. Fix a worker's file by sending it back, not by editing it.
6. **Trust level.** Worker output is unverified until the check passes, and its accuracy until a named
   person reviews it. Report what was verified and what was not.
7. **Cost.** Use the smallest capable model for workers. Run the check and the review once, at the end,
   not after every worker.
8. **Conflicts.** `candidates.py conflicts` before any question; ask for each consequential one and
   record the decision through `record.py`.
