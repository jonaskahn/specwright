# Install and package

## Universal installation

Specwright ships standard `skills/<name>/SKILL.md` folders. Each skill carries its own
scripts, private `scripts/kitlib`, references, assets and MIT license, so a normal skills
installer can copy one folder atomically without a Python pre-step.

Project install:

```sh
npx skills add jonaskahn/specwright
```

Global install, skipping prompts:

```sh
npx skills add jonaskahn/specwright -g -y
```

Claude Code plugin marketplace:

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

The plugin manifests declare all eleven skills and eleven command wrappers. Commands
carry Claude-specific `${CLAUDE_PLUGIN_ROOT}` paths; skill folders themselves remain
host-neutral. Installation writes only skill files and client metadata. It never writes
to Jira, Confluence or a Specwright workspace. Opening a skill in a client and checking
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
`--copy-mirror` to always copy. Codex, Copilot, Cursor and Gemini can discover the
canonical project skills; Claude Code uses its mirror.

New projects receive AGENTS.md, equal CLAUDE.md and GEMINI.md copies, and a Copilot
instruction pointer. Existing instructions are preserved. If a project already has
instructions, merge the Specwright standing rules manually instead of replacing them.
Any same-name skill collision stops before skill files are written. To upgrade, back up
the installation and remove only its `sw-*` folders before reinstalling. Do not install
duplicate names at user scope; lifecycle, update and removal belong to the `skills` CLI.

Then initialize a workspace using the absolute path to the installed script:

```sh
python3 /absolute/path/to/spec-repo/.agents/skills/sw-init/scripts/workspace.py init \
  --root /absolute/path/to/spec-repo --mode flat --scope REF --name Refunds \
  --jira-site https://example.atlassian.net --project-key PROJ
```

## Standalone skill archives

```sh
python3 tools/package.py --zip --out dist
```

Packaging is a plain copy of each already self-contained folder; it does not vendor code
or reach the network. Each zip contains one skill folder with its `LICENSE`, references,
assets, scripts and private `kitlib`. Release output is excluded from version control.
Existing output is never replaced; choose a fresh `--out` directory for another build.

## Optional converters

Plain text, Markdown, CSV, email and simple HTML are handled locally. For richer
documents install pandoc, Poppler tools, Tesseract, markitdown or LibreOffice as needed.
No converter is bundled. Missing tools produce explicit degraded results, not invented
document text. Review OCR output against the original, especially amounts and dates.

Run the gate list in [conventions](conventions.md) before packaging.

## Diagrams

The installed sw-draw skill renders 41 validated JSON types and ships four
illustration templates for embedding. `.svg` output is self-contained; `.html`
adds the source-value table and local spec links. Both follow system light/dark
themes. New structured types optionally use bounded CSS-only motion; no JavaScript
is shipped or executed. Re-run the skill's offline and border checkers after any
render or template edit.
