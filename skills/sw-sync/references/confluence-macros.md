# confluence macros

When pulling a mapped Confluence page, inspect its storage format before trusting the
conversion.

## Recognized macros (safe)

`info`, `note`, `warning`, `tip`, `panel`, `expand`, `code`, `jira` convert to ordinary
content.

## Unresolved macros (warnings)

Any other `<ac:structured-macro ac:name="…">` becomes a warning of the form
`unresolved-macro:<name>` and is kept, never silently dropped.

## Limits

The manifest `limits` block (`child_depth` 2, `max_pages` 50) caps recursion and page
count. Exceeding either stops the pull — a larger pull needs a deliberate manifest change,
not an automatic override.
