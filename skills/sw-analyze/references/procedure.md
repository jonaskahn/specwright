# sw-analyze — detailed procedure

Load only when a step in SKILL.md is unclear or a script errors.

## Code roots
- `roots` lists registered roots and detected candidates (the repo the workspace sits in;
  neighbouring folders with build files, including one level down for monorepos).
- `roots --add ../shop-api ../shop-web` stores them in the manifest as paths relative to the
  project folder. Code is read-only evidence; no script writes there.
- A root that disappears is reported (`exists: false`), never silently dropped.

## Inventory
- Names and pointers only: endpoints (Spring, Nest, Express, FastAPI/Flask, Django, Go, file
  routes), screens (file routes, React/Vue routes, Flutter screens), entities (JPA, Prisma,
  Django, SQLAlchemy, SQL), tests (names), doc headings (00-inbox, docs folders in roots).
- Candidates group names sharing a keyword across kinds. They are a map, not evidence.
- Large repos: files over 300 KB and generated folders are skipped; at most 20,000 files.

## Errors
- `cite` exit 2: wrong root name, path outside the root, or lines out of range.
- `check` findings: status/confidence words, missing CODE cites for done/partial/divergent,
  divergent without a Q, stale cites (the code changed: re-read and re-cite), intended without
  a source.

## Existing workspaces
A project with specs adopts code the same way: register roots, then analyse the named feature.
The analysis file sits beside the specs; sw-spec turns it into version 1 or a change.
