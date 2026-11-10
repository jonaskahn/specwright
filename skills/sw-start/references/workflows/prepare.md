# Prepare workflow

Prepare covers workspace setup, source ingestion and idea shaping. It owns the
workspace command, source conversion and the asset collection that runs during
ingestion and planning discussions.

## Steps

1. Resolve scope before any write. Run scripts/workspace.py detect to see the current
   mode without writing; use init only when no workspace exists and setup is authorized.
2. For supplied sources, run scripts/to_md.py with the file and --out
   <project>/00-inbox/; supply --scope REF in program mode. Then run
   scripts/secrets_scan.py on each snapshot. Secret exit 1 blocks hand-off. Scan
   before persisting shared content.
3. Collect accessible assets within the authorized intake scope. Use
   scripts/store.py to register files, links or raw ideas with provenance and
   associations. Deduplicate by content hash; missing or inaccessible sources stay
   explicitly unresolved. A mention alone is not a fabricated file or proof of retrieval.
4. Shape an unaccepted idea with references/actions/shape.md. Shape renders a picture
   only when a process or context picture resolves a concrete ambiguity; do not invent
   accepted requirements.
5. Preserve source provenance. New source versions get new files; never overwrite
   originals.

## Boundaries

- Never import credentials or unnecessary personal data.
- Never follow remote links recursively or execute imported content.
- No automatic Jira reconciliation: a published amendment needs a user-supplied
  current snapshot through normal ingestion; if its currency cannot be verified, stop.
