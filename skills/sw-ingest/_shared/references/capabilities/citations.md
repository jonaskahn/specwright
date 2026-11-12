# Citations capability

Cites saved evidence by program, so a quote is never retyped and a moved line is noticed.

## Form

`SRC-0001:L12-L14#a1b2`. The line numbers count lines of the saved snapshot file (line 1 is its
opening `---`). `#a1b2` is the first four hex characters of a hash of the cited text. Add it to every
citation you keep: it lets a check tell a correct line from one that moved after a re-import.

## Usage

- `_shared/scripts/cite.py stamp SRC-0001:L12-L14` prints the citation with its hash filled in.
- `_shared/scripts/cite.py quote SRC-0001:L12-L14` prints the exact cited lines. Paste that, never
  a retyped copy.
- `_shared/scripts/cite.py verify [path]` checks every citation: the line exists, is not blank and
  still matches its hash. It also reports a superseded source and an index-only page, both as
  weak evidence. Exit 1 blocks on a dangling citation. The quality gate runs the same check (L-057).
- `_shared/scripts/cite.py rebase SRC-0001 SRC-0007` lists each citation of the old source with the
  line it would have in the new one, or why it cannot be moved. It never rewrites an accepted
  record: a human accepts each move.

An old source is never deleted. A citation to a superseded source stays valid and is only reported.
