# Specwright

Portable agent skills for business analysts: turn source material into testable stories,
keep stable traceability, and prepare safe, explicitly approved Jira changes.

## Workflow

`sw-init` → `sw-ingest` → `sw-shape-idea` → `sw-spec` → `sw-draw` (when useful)
→ `sw-review` → `sw-publish` → `sw-sync`.

Use `sw-status`, `sw-trace` and `sw-lint` throughout. Jira becomes the system of record
for published story text; the repository holds source snapshots, drafts and evidence.

## Get started

Requires Python 3.10 or newer. Runtime scripts use only the standard library.

```sh
python3 tools/validate.py
python3 tools/install.py --target /path/to/spec-repo
python3 /path/to/spec-repo/.agents/skills/sw-init/scripts/workspace.py --help
```

The installer puts canonical skills in `.agents/skills` and mirrors them to
`.claude/skills`. It never overwrites existing instructions or unrelated skills.
See [installation](docs/install.md), [security](docs/security.md),
[conventions](docs/conventions.md) and [sources](docs/sources.md).

## Develop

```sh
python3 -m unittest discover -s tests -t .
uvx ruff check .
uvx ruff format --check .
python3 tools/validate.py
python3 tools/package.py --zip
```

Packages are written under `dist/`, with a private copy of the shared Python library
inside each skill. Trigger evals are fixtures, not a claim of measured model accuracy.

The publish protocol and adapters are tested against a local Jira mock. No real Jira
instance is accessed by the test suite. A sandbox trial and human sign-off are required
before production use; dashboard integration is intentionally deferred.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
