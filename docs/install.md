# Install and package

## Universal installation

Specwright ships seven public `skills/<name>/SKILL.md` folders: `sw-start`, `sw-shape`,
`sw-ingest`, `sw-spec`, `sw-plan`, `sw-review` and `sw-publish`. Shared runtime and
references live once in `skills/_shared/`. Packaging embeds a local `_shared/` copy in
each shipped folder, so an uploaded ZIP is self-contained and never depends on a sibling.

Project install:

```sh
npx skills add jonaskahn/specwright
```

Global install, skipping prompts:

```sh
npx skills add jonaskahn/specwright -g
```

Claude Code plugin marketplace:

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

Both routes read `skills/` straight from the repository, so they always carry the full
`extended` set of 20 diagram types (`skills/sw-spec` holds core and extended; only
`extras/` is left out). Only `tools/package.py` defaults to the 12-type core profile.

The plugin manifests declare all seven public skills and seven command wrappers. Commands
carry Claude-specific `${CLAUDE_PLUGIN_ROOT}` paths; skill folders themselves remain
host-neutral. Installation writes only skill files and client metadata. It never writes
to Jira, Confluence or a Specwright workspace.

A workspace may live at the repository root (docs-only) or under `.specwright/` inside a code
repository (embedded), for one project or a program of several. See the Layouts section of
the README and `docs/conventions.md`. Opening a skill in a client and checking
discovery remains a manual compatibility check because client support varies by version.

Python 3.10 or newer is required to run the shipped scripts. Runtime code uses only the
standard library; no JavaScript runtime or dependency lockfile is used.

## Offline fallback

Use the bundled installer when a checkout is air-gapped or a project wants generated
instruction files:

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
```

It copies the same self-contained skills to `.agents/skills/sw-*` and mirrors them to
`.claude/skills/sw-*` as relative symlinks on macOS/Linux or copies on Windows. Use
`--copy-mirror` to always copy. The installer ships the full `extended` profile of the
diagram types (20); pass `--profile core` for the 12 core types only. Codex, Copilot, Cursor and Gemini can discover the
canonical project skills; Claude Code uses its mirror.

New projects receive AGENTS.md, equal CLAUDE.md and GEMINI.md copies, and a Copilot
instruction pointer. Existing instructions are preserved. If a project already has
instructions, merge the Specwright standing rules manually instead of replacing them.
Any same-name skill collision stops before skill files are written. To upgrade, back up
the installation and remove only its `sw-*` folders before reinstalling. Do not install
duplicate names at user scope; lifecycle, update and removal belong to the `skills` CLI.

Then initialize a workspace using the absolute path to the installed script:

```sh
python3 /absolute/path/to/spec-repo/.agents/skills/sw-start/scripts/workspace.py init \
  --root /absolute/path/to/spec-repo --mode flat --scope REF --name Refunds \
  --jira-site https://example.atlassian.net --project-key PROJ
```

## Standalone skill archives

```sh
python3 tools/package.py --zip --out dist
```

Packaging copies each public skill and the canonical `skills/_shared/` tree, rewrites
`../_shared/` references to local `_shared/`, and writes a self-contained ZIP. It does
not reach the network. Each zip contains exactly one skill folder with its `LICENSE`,
references, assets, scripts and an embedded `_shared/kitlib`. Release output is excluded
from version control. Existing output is never replaced; choose a fresh `--out` directory
for another build.

Archives default to the `core` profile (12 diagram types) to stay well inside the upload file
cap; `--profile extended` adds the 8 extended types. The skill adapts to whichever set is
present, so either archive works without further changes.

## Optional converters

Plain text, Markdown, CSV, email and simple HTML are handled locally. For richer
documents install pandoc, Poppler tools, Tesseract or markitdown as needed.
No converter is bundled. Missing tools produce explicit degraded results, not invented
document text. Review OCR output against the original, especially amounts and dates.

anydoc and speech-to-text adapters are not enabled: their release/argv, offline mode,
resource limits and output contracts must be verified before integration. No hosted
OCR/transcription or automatic model download is a fallback. Legacy or macro-enabled
Office input requires a reviewed safe export, not merely consent to run a converter.

Workspace creation requires Git. New docs roots initialize a repository only when no
parent repository exists. Embedded layouts require and reuse the code repository,
including worktrees; no nested `.specwright/.git`, config changes or commits are made.
New workspaces default to Markdown; existing destination preferences remain intact.

Run the gate list in [conventions](conventions.md) before packaging.

## Diagrams

The installed `sw-spec` skill renders 41 validated JSON types and ships four
illustration templates for embedding. `.svg` output is self-contained; `.html`
adds the source-value table and local spec links. Both follow system light/dark
themes. New structured types optionally use bounded CSS-only motion; no JavaScript
is shipped or executed. Re-run the skill's offline and border checkers after any
render or template edit.
