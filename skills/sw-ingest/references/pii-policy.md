# Sensitive input and retention

The scanner recognizes likely Atlassian tokens, AWS keys, private PEM blocks,
JWTs and password assignments as secrets. Emails, Vietnamese mobiles, 12-digit
CCCD values and Luhn-valid card candidates are PII warnings. Patterns may miss
secrets or flag harmless samples. Review locally; never paste matched values
into chat, diagnostics or reports.

Reports expose type, one-based line and a fully masked tail, never matched text.
The tail stays fully masked because short passwords and personal identifiers
could otherwise be reconstructed. Stdout is JSON. Exit 1 means secrets found,
including after --redact. Exit 0 may still include PII. Exit 2 means argument,
decoding, read or safe-write failure.

Establish retention consent before importing known sensitive sources. The importer
refuses detected sensitive extracted text by default. --retain-sensitive-raw
permits a local copy only after explicit consent, not permission to commit or
share it. Binary originals need separate review: extraction can miss hidden data.
Restrict access to raw storage and exclude it from version control.

Scan each snapshot before hand-off. --redact writes [REDACTED:<type>] markers
atomically to --out, or to the input text if omitted. Raw originals cannot be
redacted in place. Rerun the scan and visually check contextual leaks, attachments
and metadata. For append-only snapshots redact to a separate restricted copy;
ask how to retain or withdraw the cited original rather than silently rewriting it.

If retention is rejected after import, obtain explicit permission before removing
the local raw copy. Record hash, SRC id, reason and date without content. Prefer
an approved redacted export for future imports. Never remove someone else's
source file. Redaction does not revoke an exposed credential: notify its owner
to rotate it.
