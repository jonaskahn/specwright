# Install and package

## Universal installation

Specwright ships seven public `skills/<name>/SKILL.md` folders: `sw-start`, `sw-shape`,
`sw-ingest`, `sw-spec`, `sw-plan`, `sw-review` and `sw-publish`. Shared runtime and
references live once in `skills/_shared/`. Packaging embeds a local `_shared/` copy in
each shipped folder, so an uploaded ZIP is self-contained and never depends on a sibling.

### Command-line installer

`install.sh` and `install.ps1` install every public skill without Node or Python. They do not ask which skills to install. They do ask which agents to install for, using the same agent ids and skill directories as `npx skills add`. All projects is the default. `--project` / `-Project` installs into this project only. `-y` / `-Yes` skips prompts: every detected agent is selected, or Universal (`~/.config/agents/skills`, or `.agents/skills` in this project) when none are detected.

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --project
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --agent cursor --agent claude-code -y
```

```powershell
irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1 | iex
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Project
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Agent cursor,claude-code -Yes
```

Useful flags: `--agent` / `-Agent` (repeatable or comma-separated), `--target` / `-Target` for the project directory, `--list-agents` / `-ListAgents`. `SPECWRIGHT_REPO`, `SPECWRIGHT_REF`, `SPECWRIGHT_URL` and `SPECWRIGHT_ROOT` choose the source tree. `SPECWRIGHT_INSTALL_YES=1` is the same as `-y` / `-Yes`. `NO_COLOR` turns the framed screen off.

macOS and Linux need `curl` or `wget`, plus `tar`. Windows needs PowerShell and `tar`. When the script file itself sits inside a Specwright checkout, that checkout is the source. A piped download uses GitHub `main` unless the variables above say otherwise.

On macOS and Linux, one destination is a real copy (preferring `.agents/skills` when it is selected) and other destinations on the same disk become relative symlinks. Windows always copies. The installer writes skill folders only. It does not write `AGENTS.md`, `CLAUDE.md` or plugin files.

If a selected destination already has a Specwright `sw-*` skill, that folder is removed and the new copy is installed. A same-named folder that is not a Specwright skill stops the install. Run the installer again to update.

### Skills CLI

All projects:

```sh
npx skills add jonaskahn/specwright -g
```

This project:

```sh
npx skills add jonaskahn/specwright
```

Claude Code plugin marketplace:

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

Both routes read `skills/` straight from the repository. Each skill folder carries its own
generated `_shared/` copy, so installing a skill on its own works. They always carry the full
`extended` set of 20 diagram types (`skills/sw-spec` holds core and extended; only
`extras/` is left out). Only `workshop/tools/package.py` defaults to the 10-type core profile.

The plugin manifests declare all seven public skills and seven command wrappers. Commands
carry Claude-specific `${CLAUDE_PLUGIN_ROOT}` paths; skill folders themselves remain
host-neutral. Installation writes only skill files and client metadata. It never writes
to Jira, Confluence or a Specwright workspace.

A workspace may live at the repository root (docs-only) or under `.specwright/` inside a code
repository (embedded), for one project or a program of several. See the Layouts section of
the README and `docs/conventions.md`. Opening a skill in a client and checking
discovery remains a manual compatibility check because client support varies by version.

Python 3.10 or newer is required to run the skill scripts. `install.sh` and `install.ps1` do not need it. Runtime code uses only the
standard library; no JavaScript runtime or dependency lockfile is used.

## Offline fallback

Use the bundled installer when a checkout is air-gapped or a project wants generated
instruction files:

```sh
python3 workshop/tools/install.py --target /absolute/path/to/spec-repo
```

It copies the same self-contained skills to `.agents/skills/sw-*` and mirrors them to
`.claude/skills/sw-*` as relative symlinks on macOS/Linux or copies on Windows. Use
`--copy-mirror` to always copy. The installer ships the full `extended` profile of the
diagram types (20); pass `--profile core` for the 10 core types only. Codex, Copilot, Cursor and Gemini can discover the
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
python3 workshop/tools/package.py --zip --out dist
```

Packaging copies each public skill and the canonical `skills/_shared/` tree, rewrites
`../_shared/` references to local `_shared/`, and writes a self-contained ZIP. It does
not reach the network. Each zip contains exactly one skill folder with its `LICENSE`,
references, assets, scripts and an embedded `_shared/kitlib`. Release output is excluded
from version control. Existing output is never replaced; choose a fresh `--out` directory
for another build.

Archives default to the `core` profile (10 diagram types) to stay well inside the upload file
cap; `--profile extended` adds the 8 extended types. The skill adapts to whichever set is
present, so either archive works without further changes.

Check an archive set with `python3 workshop/tools/verify_package.py --dist dist` (`make package`
runs it). It unzips every skill, fails on any `references/`, `scripts/` or `assets/` file a
text names but the zip lacks, and starts each script with `--help`. If a host drops the
`_shared` folder on upload, every script stops with "shared library missing at ...; reinstall
this skill from a zip that includes its `_shared` folder" instead of a bare import error.
Each `_shared/` also carries `MANIFEST.json` (the kit version and a hash of every shared
file). `sw-start` checks it first and stops with the reinstall command when a file is missing,
changed or from another release.

Each skill carries the record shapes it writes under `assets/` (`snapshot.md`, `q.md` and
`cr.md` in sw-ingest; `q.md` and `dec.md` in sw-shape). Questions, decisions, reservations and
splits are written by `_shared/scripts/record.py`, which fills these fields itself. The ID registry and the traceability
matrix are generated by `scripts/workspace.py` and the trace capability, so they have no
template file.

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
