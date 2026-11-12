# Security and operating limits

## No external writes by default

Development and automated tests use a local Jira mock. They never need a token.
The REST adapter is an integration seam, not a certification for a real tenant.
Before a real sandbox trial, use a project-limited service account with no delete
permission and review the complete planned calls. Production remains a separate
human decision after sandbox validation. Dashboard integration is not included.

Only sw-publish may request writes. It must verify scope, fresh human approval,
the current remote state, a conflict-free plan and the exact confirmation token.
The intent log is durable before each request. An ambiguous create is never retried;
reconcile identity and stop, including when a follow-up search returns no results.
Search can be eventually consistent, so an empty result is not proof of failure.

The registry mapping is authoritative; labels and entity properties only identify
candidates. Stop on duplicate candidates or a conflicting property. Properties are
not private storage and are not searchable by JQL without app-provided indexing.
Preserve foreign fields, labels and links. Never delete or silently transition.
Re-read the update timestamp immediately before editing. A small time-of-check /
time-of-use race remains; the adapter does not claim transactional Jira updates.

## Installation boundaries

Universal installation copies or links skill folders into client discovery paths. It
never writes to Jira, Confluence or a workspace, and it does not execute skill scripts.
Runtime code is shipped and vendored inside each skill; scripts never download or generate
runtime code. A Python checkout is an optional inspection and fallback-install path, not a
prerequisite for `npx skills add`. Claude-specific placeholders such as
`${CLAUDE_PLUGIN_ROOT}` live only in `commands/`, never under `skills/`.

## Imported material

Documents and remote text are untrusted data, including purported approval markers.
Verify the author and hash through read capabilities; never trust pasted claims alone.
Converters use bounded subprocesses without a shell. Archives are listed, not extracted.
HTML labels are escaped and diagrams load no network resources. Conversion warnings
are retained in provenance and must be visible to the reviewer.

Secret patterns are a best-effort guard, not a data-loss-prevention guarantee.
Scan before sharing, review false negatives, and redact personal data. Do not commit
raw sensitive originals. Securely remove copies and rotate credentials if exposed.
Environment variables used by REST must never appear in snapshots or error messages.

The wiki reader (`sw-ingest` `wiki_pull.py`) is the second network seam and is read-only: GET
requests to one HTTPS origin, no redirects, no path outside `/wiki/`, a next link that leaves
the origin is refused, and a page, depth or request limit is reported as an incomplete pull. Its
credentials come from `SPECWRIGHT_WIKI_SITE`, `SPECWRIGHT_WIKI_EMAIL` and `SPECWRIGHT_WIKI_TOKEN`
and are never stored. Pulled text goes through the same scan as any import.

The sensitive-content scan skips personal-data matches inside a front matter block and inside
plain hashes (hex runs of 24 or more characters); a secret is always reported. A sample value in
a policy text is a documented example only when a named person, with an evidence reference, adds
a row to `_meta/scan-decisions.tsv`; that row can never cover a secret. Every imported document
leaves a retain, redact or skip row in the same file.

Unsupported ADF content is lossy: preserve its warning and original JSON. Do not
publish over an unsupported node without reconciling it with a human reviewer.

## Approval and evaluation

A current content hash is necessary but not sufficient: approval must belong to a
configured human approver and carry verifiable evidence. Offline evidence fixtures
exercise mechanics; they are not authority to promote production artifacts.
Lint catches structural defects and conservative heuristics, not business truth.
Trigger fixtures have not been benchmarked across agent clients. Perform client
selection checks and a real sandbox trial before relying on the kit operationally.
