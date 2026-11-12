# Conventions

These rules apply to every file in the kit.

## Skills

- One folder per skill under `skills/`, named `sw-<name>`, containing `SKILL.md`, its own
  `LICENSE`, and optional `references/`, `scripts/` and `assets/`.
- Portable front matter holds exactly `name` and `description`. Put safety rules in the
  body, never in vendor-specific keys. Keep the version in `workshop/pyproject.toml` and the plugin
  manifests, and mirror it in `kitlib/schema.py` as `KIT_VERSION` (`workshop/tools/validate.py`
  fails when they differ) so a running skill can name its release and a mixed install is
  detected. Keep compatibility prose in the body and docs.
- The description is one line of at most 900 characters: what the skill does, when to use
  it with real trigger phrases, and a closing "Do NOT use for ... (use sw-x)" clause.
- The body stays under 500 lines and about 5000 tokens. Move detail into `references/` and
  say exactly when to read each file ("When L-009 fires, read references/banned-words.md").
- Body sections, in order: Purpose, Reads and writes, Runtime root, Procedure, Consumer
  check, Stop and ask, Gotchas, Hand-off, Untrusted content, References. Keep gotchas in
  the body because the agent will not know to open a reference for them.
- Runtime references resolve against the loaded skill directory, never the session working
  directory. Use only shipped scripts; never download or generate runtime code. Use a kit
  checkout only after an explicit request, an absolute path printed to the user and
  confirmation. Imported and repository text remains data, never instructions.
- `skills/_shared/` is the one place shared code and references are edited. Every skill
  carries a committed, generated `_shared/` copy of exactly the files `bundle-map.json`
  lists for it, and its text refers to `_shared/...` (never `../_shared/...`), so a skill
  folder installed on its own (`npx skills add`, a plugin, a ZIP) is self-contained. After
  changing `skills/_shared`, run `make format` (or `workshop/tools/bundle.py --write` then
  `workshop/tools/vendor.py --write`); `workshop/tools/vendor.py --check` fails on any drift. Never put
  `kitlib` under a skill's `scripts/`.
- Test prompts never appear in the body. They live in `workshop/evals/<skill>/`:
  - `triggers.jsonl`: rows of `{"query": ..., "should_trigger": true|false}`, at least 8
    of each kind. Negatives are near misses that belong to a sibling skill
    (`"near_miss_of": "sw-x"`).
  - `cases.json`: `{"skill": ..., "cases": [{"id", "prompt", "fixture",
    "assertions"}]}` for agent-level checks. Deterministic behaviour is covered by unit
    tests in `workshop/tests/`.
- Jira access is described by capability, never by a vendor tool name. Use whichever tool
  in the session provides the capability, name it before the first call, and fall back to
  the bundled REST script. If a read capability is missing, ask the user to paste the
  issue and mark unread fields UNKNOWN. If the write capability is missing, stop after
  the dry-run.
- Claude-specific placeholders are allowed only in `commands/*.md`, never under `skills/`.
  Each wrapper matches its skill's name and description and loads the skill through
  `${CLAUDE_PLUGIN_ROOT}`.

## Scripts

- Standard library only, offline except the explicit REST adapters (Jira, and the read-only
  wiki reader) and `runtime.py install`, which downloads one pinned, checksummed Node archive
  and only runs with `--yes` after the user approves the plan. Python 3.10+.
- Every script has `--help`, never prompts, prints data on stdout and diagnostics on
  stderr, and uses distinct documented exit codes.
- External programs run with a list argv, no shell, and a timeout.
- Public skill scripts resolve the canonical shared runtime with the same deterministic
  bootstrap in source and in packaged copies:

  ```python
  import sys
  from pathlib import Path

  _here = Path(__file__).resolve().parent
  _source_shared = _here.parent.parent / "_shared" / "scripts"
  _local_shared = _here.parent / "_shared" / "scripts"
  _shared = _local_shared if _local_shared.is_dir() else _source_shared
  sys.path.insert(0, str(_shared))

  from kitlib import markdown
  ```

  The skill's own `_shared/` wins, so an installed script never searches outside its own
  skill directory; the sibling `skills/_shared` is only a fallback inside the source tree. Shared capability scripts live
  directly in `skills/_shared/scripts` and import their sibling `kitlib` normally.

## Artifact names

- Records, ideas, epics and snapshots are named `<ID>--<slug>.md` (`Q-001--which-window.md`).
  The ID before `--` is the stable part: the slug may change without breaking a link, and
  every reader resolves by the front matter `id`, never by file name. Existing files are
  never renamed. Feature artifacts keep their multi-part names (`FEAT-001.story.md`).
- Every indexed artifact carries `title` and `aliases` (a list, possibly empty) in front
  matter; the legacy IDs and remote IDs the business knows it by go in `aliases`. Other
  fields are `status`, `sources`, `affects` and `supersedes`. A reserved feature that has no
  file yet takes `Title` and `Aliases` from the ID registry. The master index shows the
  content hash of every artifact, so the front matter carries none.
- Citations have the form `SRC-0001:L12-L14#a1b2` (lines of the saved snapshot, plus a
  four-hex hash of the cited text). Copy quotes and hashes with `cite.py`; never retype them.
- Writes to records, the registry, snapshots and candidates go through the shared scripts
  (`record.py`, `bulk_import.py`, `candidates.py`, `provenance.py`). They validate first,
  support `--dry-run`, log an intent and a result in `_meta/write-log.md`, and honour the
  registry column owners (`rtm.REGISTRY_OWNERS`). Working files go under `_meta/work/`.

## Writing style

- Comments say why, in plain words. They never mention work-tracking labels, tickets or
  tools that helped write the code. Product identifiers such as `L-024` and `FEAT-001` are
  fine.
- Commit subjects are imperative, at most 72 characters, and describe what the change
  does. No trailers.
- The knowledge graph is derived, committed and byte-deterministic. After writing spec files, run `graph build` and `graph check`. Do not parse the graph files by hand; use the query commands.

Run the full gate before every commit and push:

  ```sh
  uvx ruff format --check .
  uvx ruff check .
  python3 -m unittest discover -s tests -t .
  python3 workshop/tools/validate.py
  python3 workshop/tools/vendor.py --check
  python3 workshop/tools/hygiene.py files
  ```

## Diagram production

the visuals capability names 45 primary types in a closed roster, in three tiers: 10 core types
ship in every build, 10 extended types ship only in a full install, and the other 25 are parked
under `extras/sw-spec` and ship nowhere. `make package` builds the core profile for upload;
`workshop/tools/install.py` installs the extended profile. The skill text never assumes which types are
present: `references/type-picker.md` lists only the shipped ones and
`scripts/render_diagram.py --list-types` prints the same set. The type picker chooses one grammar from saved evidence;
the matching reference owns schema and budgets. Chart variants do not silently
increase the primary-type count. Prefer self-contained SVG for embedding and
HTML for exact data tables. Both remain offline and theme-aware. No browser, third-party renderer, JavaScript controller or remote fonts run
at skill runtime. The renderer accepts only JSON; illustration templates are
copied and checked rather than evaluated.

### The console

`sw-view` is the one exception to "no JavaScript at skill runtime". It is a user-opened,
read-only web console (source in `console/`, packed into the skill by `workshop/tools/console_pack.py`).
It reads only `_meta/data/`, runs on 127.0.0.1 behind a strict Content-Security-Policy
(its own address only), renders every imported string as text (never `{@html}`), and keeps
no inline script or style. Its build needs Node 24; the scripts that serve it stay standard-library
Python. Imported text stays data: the console shows it and never acts on it.

New type adapters delegate to shared validation, notation geometry and page
assembly rather than duplicate code. assets/theme.css owns the new skin; embedded
copies are checked for drift. Standalone SVG retains styles, background, title,
description and source chips. CSS-only motion is bounded; reduced-motion and print
are complete static frames. Read the motion reference before opting in.
