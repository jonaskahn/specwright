# Specwright

Portable agent skills that carry a software idea all the way to implementation-ready
work. Start from raw source material or a rough idea, shape it, specify it with testable
criteria, draw it, break it into stories and tasks, and keep every item traceable.

## What it is for

Specwright covers the path from idea to implementation tasks for any software team, not
only business analysis: product owners, engineers, QA and technical leads all work from
the same stable IDs and evidence. The skills are agent-neutral and install in any client
that reads the standard `SKILL.md` format.

Each deliverable can be produced in either form, or both:

- **Detailed Markdown** specs, stories and task breakdowns kept in the repository, with
  source snapshots, drafts and evidence beside them.
- **Jira stories and tasks** created or updated through a guarded publish flow: quality
  gate, three-way dry-run and typed confirmation for the exact plan.

Today's skills cover ideation, specification, diagrams, review, publication and
traceability. Skills that break work down further for developers can be added to the
same workflow without changing the IDs, traceability or safety rules.

## Workflow

`sw-init` → `sw-ingest` → `sw-shape-idea` → `sw-spec` → `sw-draw` (when useful)
→ `sw-review` → `sw-publish` → `sw-sync`.

Use `sw-status`, `sw-trace` and `sw-lint` throughout. Work stays in Markdown until you
choose to publish. Once a story is published, Jira is the system of record for its text;
the repository holds source snapshots, drafts and evidence.

## Diagrams and illustrations

sw-draw routes 45 primary types: 41 structured JSON renderers and four original
illustration templates. Use standalone SVG for embedding or offline HTML for
source-value tables and spec navigation. Both support light/dark themes; new
structured types optionally use bounded, reduced-motion-safe CSS cues, never JS.
Marimekko, dumbbell, funnel and distribution/rank variants are grouped within
primary chart types. No source quantity, policy or approval is inferred.

See the installed skill's type-picker reference for the full catalog, contracts,
complexity limits and template routing. sw-trace supplies authoritative RTM facts;
a diagram never changes requirement status or authorizes a remote write.

## Install

Requires Python 3.10 or newer for runtime scripts. Runtime code uses only the standard
library. No Python install step is needed: every skill folder is self-contained.

Project installation with the portable skills CLI:

```sh
npx skills add jonaskahn/specwright
```

For user-level installation across projects:

```sh
npx skills add jonaskahn/specwright -g -y
```

Claude Code users can install the plugin marketplace route:

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

Both routes expose the same eleven `sw-*` skills. Verify skill discovery in your agent
client and version; selection behavior is client-specific and manual.

### Offline fallback

For an air-gapped checkout or a project that needs the generated instruction copies:

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
python3 tools/package.py --zip --out dist
```

The installer writes `.agents/skills/sw-*` and a `.claude/skills` mirror. It never
overwrites existing instructions or unrelated skills. Standalone archives are release
artifacts: each zip contains one self-contained skill folder.

See [installation](docs/install.md), [security](docs/security.md),
[conventions](docs/conventions.md) and [sources](docs/sources.md).

## Develop

```sh
uvx ruff format --check .
uvx ruff check .
python3 -m unittest discover -s tests -t .
python3 tools/validate.py
python3 tools/vendor.py --check
python3 tools/hygiene.py files
```

Run `python3 tools/vendor.py --write` after changing `lib/kitlib`, the shared safety
references or the repository license. Trigger evals are fixtures, not a claim of
measured model accuracy.

The publish protocol and adapters are tested against a local Jira mock. No real Jira
instance is accessed by the test suite. A sandbox trial and human sign-off are required
before production use; dashboard integration is intentionally deferred.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
