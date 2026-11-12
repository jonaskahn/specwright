# Assets capability

Keeps user-provided files, links, diagrams, mockups and raw ideas in the resolved
project so later steps can cite them instead of re-describing them.

Kinds of asset and how each is registered: _shared/references/asset-kind.md.

## Trigger

Runs during every ingestion batch and during planning discussion. In a batch, inspect
supplied attachments, images, diagrams, document references and relevant links. In
discussion, detect newly supplied or mentioned concrete assets as they appear.

## Collection rules

1. Scan for secrets and personal data before persisting shared content.
2. Collect accessible assets within the authorized intake scope and preserve source
   provenance.
3. Deduplicate by content hash and source identity; retain stable ASSET IDs; associate
   each asset with its source and affected items; preserve new versions rather than
   overwriting originals.
4. Distinguish collected files, reference-only assets, inaccessible sources and
   proposed assets that do not yet exist. A mention alone is not a fabricated file.
5. Include newly collected assets and their relationships in the next graph update.
   Report collected, reused and unresolved counts succinctly.

## Usage

Run _shared/scripts/store.py with --root <project> and the resolved scope. Classify the
asset with _shared/references/asset-kind.md. For a link, use --source URL; do not fetch
remote content. For local files, the script copies the bytes and registers the hash.
Duplicate bytes report the existing asset instead of allocating a new one.
