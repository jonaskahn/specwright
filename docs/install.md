# Install and package

## Universal installation

Specwright ships five public `skills/<name>/SKILL.md` folders: `sw-start`, `sw-craft`,
`sw-forge`, `sw-ship` and `sw-view`. Shared runtime and
references live once in `skills/_shared/`. Packaging embeds a local `_shared/` copy in
each shipped folder, so an uploaded ZIP is self-contained and never depends on a sibling.

### Command-line installer

`install.sh` and `install.ps1` install every public skill without Node or Python. They do not ask which skills to install. They do ask which agents to install for, using the same agent ids and skill directories as `npx skills add`. All projects is the default. `--project` / `-Project` installs into this project only. `-y` / `-Yes` skips prompts: every detected agent is selected, or Universal (`~/.config/agents/skills`, or `.agents/skills` in this project) when none are detected.

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --project
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --agent cursor --agent claude-code -y
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --version 0.9.0
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --branch v0.9
```

```powershell
irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1 | iex
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Project
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Agent cursor,claude-code -Yes
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Version 0.9.0 -Yes
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Branch v0.9 -Yes
```

Useful flags: `--agent` / `-Agent` (repeatable or comma-separated), `--target` / `-Target` for the project directory, `--branch` / `-Branch` for a branch, `--tag` / `-Tag` or `--version` / `-Version` for a release, `--latest` / `-Latest` for the main branch, `--list-agents` / `-ListAgents`. `SPECWRIGHT_REPO`, `SPECWRIGHT_BRANCH`, `SPECWRIGHT_TAG`, `SPECWRIGHT_VERSION`, `SPECWRIGHT_REF`, `SPECWRIGHT_URL` and `SPECWRIGHT_ROOT` choose the source tree. `SPECWRIGHT_INSTALL_YES=1` is the same as `-y` / `-Yes`. `NO_COLOR` turns the framed screen off.

### Installing a branch or a version

With no source flag the installer uses the `main` branch, and takes it from the checkout around the script when there is one.

`--branch <name>` / `-b` installs any branch: `main`, `v0.9`, `dev`. `--tag <name>` / `-t`, and `--version <v>`, install a release tag. At most one of `--branch`, `--tag` and `--version` may be given; passing two stops the install before it asks anything.

`0.9.0`, `v0.9.0`, `SPECWRIGHT_TAG=v0.9.0` and `SPECWRIGHT_VERSION=v0.9.0` all mean the tag `v0.9.0`; `SPECWRIGHT_BRANCH=v0.9` is the same as `--branch v0.9`. A tag is tried first when one was asked for, and a branch falls back to the tag namespace, since a branch can be named `v0.9`. A name that does not exist stops the install with `no branch or tag <name>` or `no tag <name>` plus the list URL, before anything is unpacked. A branch name is checked for URL safety first: a leading dash, a space, a shell metacharacter or a `..` segment is refused.

A named branch or tag always downloads, even when the script runs from inside a checkout — that ref decides what lands, not this machine's tree. It also installs the skills that ref shipped, not this branch's list: `v0.9.0` ships nine skills, while `main` ships five (`sw-start`, `sw-craft`, `sw-forge`, `sw-ship`, `sw-view`), so pinning an older ref gives you that ref's layout. `--latest` / `-Latest` is the default source: it pins nothing, reuses a checkout the way a plain install does, and cannot be combined with the other three. `SPECWRIGHT_REF` still sets the ref for a plain, unpinned install.

Tags pushed after the release commit only exist when they are pushed: check `https://github.com/<repo>/tags` if a version is reported missing.

macOS and Linux need `curl` or `wget`, plus `tar`. Windows needs PowerShell and `tar`. When the script file itself sits inside a Specwright checkout, that checkout is the source. A piped download uses GitHub `main` unless a source flag or the variables above say otherwise.

On macOS and Linux, one destination is a real copy (preferring `.agents/skills` when it is selected) and other destinations on the same disk become relative symlinks. Windows always copies. Each destination also gets the `sw-*` command wrappers from `commands/`, written into the sibling `commands/` folder (`~/.claude/commands/`, `<project>/.claude/commands/`, …) with `${CLAUDE_PLUGIN_ROOT}/skills/` rewritten to the absolute path of that destination's skills, so `/sw-start`, `/sw-continue` and the rest work outside the plugin. Wrappers are always copies, never symlinks, and a wrapper your own file replaced is refused rather than overwritten. The installer writes skill folders and command wrappers only. It does not write `AGENTS.md`, `CLAUDE.md` or plugin files.

Every selected destination is a clean replacement, not a file overlay: the installer removes
the entire previous Specwright skill folders, including retired names, stale scripts, caches
and obsolete command wrappers, then installs only the selected release's files. It stages the
new release before moving the old entries aside, restores them if installation fails, and
deletes the backups after success. Symlinks are replaced as links, never recursively deleted
through their targets. `sw-*` is reserved for Specwright in these install directories: every
matching file, folder or link is replaced, even if it has no valid `SKILL.md`. Unrelated skills, project
instructions and `.specwright/` data are untouched. Cleanup applies only to the selected scope
and destinations; run the installer for each other installation you want to update.

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
`extended` set of 45 diagram types (`skills/sw-craft` holds the core set; the parked types
in `extras/sw-craft` extend a package). Only `workshop/tools/package.py` defaults to the
10-type core profile.

The Skills CLI, plugin manager and manual ZIP uploads control their own update behavior;
repository code cannot guarantee that those external tools prune retired skill names. For a
guaranteed clean upgrade of directory installs, rerun `install.sh`, `install.ps1` or the offline
installer below for the same destinations. When switching away from a CLI/plugin-managed
install, uninstall that Specwright package through its manager first, then install the new
copy; do not leave two managers publishing the same skill names. For manual ZIP updates,
remove the previous Specwright skill folders (including retired skills) before extracting
the new set; never unzip over old folders. Never delete the whole shared skills directory.

The plugin manifests declare all five public skills and six command wrappers (the five
skills plus `sw-continue`). Commands carry Claude-specific `${CLAUDE_PLUGIN_ROOT}` paths;
skill folders themselves remain host-neutral. A local install rewrites those paths to
absolute ones, so the same wrappers work without the plugin — see above. Installation writes
skill files, command wrappers and client metadata. It never writes to Jira, Confluence or a
Specwright workspace.

A workspace always lives under `.specwright/` in the repository, for one project or a program
of several. See the Layouts section of
the README and `docs/conventions.md`. Opening a skill in a client and checking
discovery remains a manual compatibility check because client support varies by version.

Python 3.10 or newer is required to run the skill scripts. `install.sh` and `install.ps1` do not need it. Skill scripts use only the
standard library.

`sw-view` also needs Node 24 or newer, to build its console once per project. Both runtimes are checked by a shell script that does not need
Python (`sh skills/_shared/scripts/runtime.sh check`, or `runtime.ps1` on Windows), because a Python check cannot report that Python is
missing. `sw-start` runs it first and, only after you approve the exact plan, installs a pinned, checksum-verified Node into
`~/.specwright/runtime/` (no administrator rights, no PATH change). Python is installed only through Homebrew or winget; on Linux the
script prints the `sudo` command for you to run. Declining leaves every other skill working. The console is generated into `<spec root>/console/` and, like `.metadata/data/`, git-ignores itself. A docs-site
generator that scans `docs/` should exclude `console/`.

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
Re-running the offline installer performs the same clean replacement for both project skill
locations, removes retired Specwright skills and wrappers, and writes current command wrappers.
Every `sw-*` entry in those skills and commands directories is replaced. New files are staged first; failed skill or
wrapper writes restore the old install. Existing project instruction files are preserved.
Do not install duplicate names at user scope.

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
`cr.md` in sw-craft; `q.md` and `dec.md` in sw-craft). Questions, decisions, reservations and
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

The installed `sw-craft` skill renders 41 validated JSON types and ships four
illustration templates for embedding. `.svg` output is self-contained; `.html`
adds the source-value table and local spec links. Both follow system light/dark
themes. New structured types optionally use bounded CSS-only motion; no JavaScript
is shipped or executed. Re-run the skill's offline and border checkers after any
render or template edit.
