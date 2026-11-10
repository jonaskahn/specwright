# SPECWRIGHT

> Idea to implementation-ready work, one cartridge at a time.

![logo](logo.svg)

Agent skills that carry a software idea from source material to implementation-ready
work. Start rough, shape it, write testable specs, draw it, break it into stories and
tasks, and keep every item traceable — as detailed Markdown, Jira issues, or both.

## CARTRIDGES

| Cartridge | What it does |
| --- | --- |
| `sw-start` | Detect the workspace and hand off to the right skill |
| `sw-asset` | Register user-provided references |
| `sw-ingest` | Snapshot documents, issues and web pages |
| `sw-shape-idea` | Turn a rough idea into a shaped concept |
| `sw-spec` | Write testable specs and acceptance criteria |
| `sw-draw` | Render 45 diagram types as offline SVG or HTML |
| `sw-plan` | Break work into stories, features and tasks |
| `sw-review` | Record named human approval |
| `sw-publish` | Guarded publish to Markdown, Jira, or both |
| `sw-sync` | Reconcile local snapshots with Jira |
| `sw-graph` | Build and query the traceability graph |
| `sw-status` | Show scope and item state |
| `sw-trace` | Trace requirements through the graph |
| `sw-lint` | Run deterministic quality gates |

## INSERT COIN

Requires Python 3.10 or newer. Every skill folder is self-contained.

```sh
npx skills add jonaskahn/specwright
```

User-level install:

```sh
npx skills add jonaskahn/specwright -g -y
```

Claude Code plugin route:

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

Start with `sw-start`; it detects the workspace and hands over to the right skill.

Offline fallback:

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
python3 tools/package.py --zip --out dist
```

See [installation](docs/install.md), [security](docs/security.md),
[conventions](docs/conventions.md) and [sources](docs/sources.md).

## DEVELOP

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

## LICENSE

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
