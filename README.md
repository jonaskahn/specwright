# Specwright

Portable agent skills for business analysts: turn source material into testable stories,
keep stable traceability, and prepare safe, explicitly approved Jira changes.

## Workflow

`sw-init` → `sw-ingest` → `sw-shape-idea` → `sw-spec` → `sw-draw` (when useful)
→ `sw-review` → `sw-publish` → `sw-sync`.

Use `sw-status`, `sw-trace` and `sw-lint` throughout. Jira becomes the system of record
for published story text; the repository holds source snapshots, drafts and evidence.

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
