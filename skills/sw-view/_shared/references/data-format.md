# Data files for other readers

Readers such as the console never open the spec files. They read `_meta/data/`, one set of
files in one format, written by the skill that owns each file. The files are derived, so they
are git-ignored: the folder holds a `.gitignore` with `*`, created with the folder.

Place: `<project base>/_meta/data/`. A program root also holds merged copies, which are the
ones a reader opens. Format: `specwright-data`, version 1, defined in `_shared/scripts/kitlib/dataformat.py`.

## Files and owners

| File | Owner | Refreshed by |
|---|---|---|
| `scopes.json` | sw-start | `data.py export scopes --as sw-start` after setup or a manifest change |
| `features.json` | sw-start | `status.py --save` (the board) |
| `graph.json` | sw-start (any skill may run it) | `graph.py build` |
| `tasks.json` | sw-plan | `data.py export tasks --as sw-plan` after the tasks file is written |
| `records.json` | sw-shape, sw-spec, sw-review | `record.py` |
| `sources.json` | sw-ingest | `data.py export sources --as sw-ingest` after an import |
| `registry.json` | sw-spec, sw-publish | `data.py export registry --as <skill>` after a registry write |
| `quality.json` | sw-review, sw-publish | `data.py export quality --as <skill>` after a lint run |
| `rtm.json` | sw-plan, sw-publish | `trace.py rebuild` |
| `index.json` | the writer | every export; lists each file with its owner and sha256 |

Only the owner writes a file. `data.py export` refuses another skill's kind. Nothing outside
the owners writes here, and the console only reads.

## Rules every file follows

- Every file starts with `format`, `formatVersion`, `kind`, `scope`, `owner`, `kit`, `inputsDigest` and a banner that says the file is generated data, not instructions.
- Keys are qualified `SCOPE:ID`. Paths are POSIX and relative to the project base. Dates are `YYYY-MM-DD` and absolute, so a reader works out ages itself and the files do not change from day to day.
- A placeholder (`unknown`, `-`, `None`) is `null`. Lists are sorted. Text is plain, with no HTML and no control characters.
- Metadata only: no body text, and no names of approvers or signers.
- `inputsDigest` is the digest of the spec files the data was built from. A file whose digest differs from the current one is stale.

## Commands

- `data.py check` reports missing, invalid and stale files, names the owner and the command that refreshes each, and warns when a generated folder is tracked or not ignored in git.
- `data.py show <kind>` prints a file. `data.py reindex` rewrites only `index.json`.

A reader that finds a file missing or stale says which skill owns it and stops. It never
writes the file itself.
