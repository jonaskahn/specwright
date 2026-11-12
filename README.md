<p align="center">
  <img src="logo.svg" alt="Specwright — interlocking geometric shapes in a ring, with a dot that travels once around its edge" width="112" />
</p>


<h1 align="center">SPEC-WRIGHT</h1>

<p align="center">
  <strong>From raw idea to implementation-ready work.</strong><br />
  Seven portable agent skills. One trail of evidence.<br />
</p>


<p align="center">
  <code>SHAPE</code> &nbsp;▸&nbsp; <code>SPEC</code> &nbsp;▸&nbsp; <code>REVIEW</code> &nbsp;▸&nbsp; <code>PLAN</code> &nbsp;▸&nbsp; <code>MARKDOWN READY</code><br />
  <sub>Publishing is a separate yes, after the plan passes.</sub>
</p>


<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="No external dependencies" src="https://img.shields.io/badge/Dependencies-Standard%20Library-64748B?style=flat-square" />
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-D7263D?style=flat-square" />
</p>


---

## `01` — What you get

A rough idea goes in. A story, a plan, and a task list come out. Product, engineering, and QA can read the same files.

- Each skill stands on its own and travels with your agent.
- Work is saved in files, so the next chat can pick up where this one stopped.
- IDs stay put. A withdrawn ID becomes a tombstone and is never reused.

| You ask for | Skill | You get |
| --- | --- | --- |
| Start or resume | `sw-start` | A board for one item, and a guarded next step |
| Ingest evidence | `sw-ingest` | A frozen snapshot, plus quoted impacts. The story stays as it is |
| Shape | `sw-shape` | A problem-led brief, an accepted split, and reserved features |
| Specify | `sw-spec` | Requirements and acceptance criteria you can observe. Diagrams when they help |
| Review | `sw-review` | Approval tied to a person, an item, a link, and a content hash |
| Plan | `sw-plan` | An approach and tasks checked against the current story |
| Publish | `sw-publish` | A delivery you asked for, including a guarded Jira write |

## `02` — Install

Four ways in. Pick the one that matches the machine in front of you.

- **To install the skills:** `curl` or `irm`. No Node, no Python.
- **To run the skills:** Python 3.10+ and Git. The standard library is enough.
- **Richer documents** can use local tools such as pandoc. A missing tool says so. It never invents the document.

A new docs workspace starts a Git repo only when it is not already inside one. An embedded workspace reuses the code repo, including worktrees. Setup does not change Git config, stage files, or commit. New workspaces default to Markdown.

### Command-line installer

> [!TIP]
> The easy door. All seven skills, for the agents you pick. All projects is the default.

All projects:

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh
```

This project:

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --project
```

Named agents, no questions:

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --agent cursor --agent claude-code -y
```

Windows, all projects:

```powershell
irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1 | iex
```

Windows, this project:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Project
```

Windows, named agents, no questions:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Agent cursor,claude-code -Yes
```

- macOS and Linux need `curl` or `wget`, plus `tar`. Windows needs PowerShell and `tar`.
- All projects is the default. `--project` / `-Project` installs into this project only.
- Skip the questions with `-y` / `-Yes`. Detected agents are used. If none show up, Universal gets the skills.
- A checkout that contains the installer is the source. Otherwise the script downloads `main`.
- An existing Specwright `sw-*` skill is replaced. A same-named folder that is not Specwright stops the install.

### Skills CLI

> [!NOTE]
> Same seven skills, through `npx`. Node comes along for the ride.

All projects:

```sh
npx skills add jonaskahn/specwright -g
```

This project:

```sh
npx skills add jonaskahn/specwright
```

This path and the Claude plugin install the skills as they are in the repo, including all 20 diagram types. Zip builds from `tools/package.py` default to the smaller set of 10.

### Claude Code plugin

> [!NOTE]
> Claude Code, from the marketplace.

Add the marketplace:

```text
/plugin marketplace add jonaskahn/specwright
```

Install the plugin:

```text
/plugin install specwright@specwright
```

### Air-gapped installation

> [!WARNING]
> No network. A checkout, Python 3.10+, and a couple of local scripts.

Install into a project:

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
```

Build skill zips:

```sh
python3 tools/package.py --zip --out dist
```

This one also writes project instruction files.

### Talk to your agent

Plain language is enough. `sw-start` finds the workspace and sends you to the right skill.

```text
"start a spec for the refunds flow"
"turn this doc into testable acceptance criteria"
"draw the refunds flow as a diagram"
"resume REF:FEAT-004"
"show the board for EPIC-001"
"send FEAT-004 to review"
"plan FEAT-004 after its approval"
"step FEAT-004 back to spec"
"does this new policy conflict with FEAT-004?"
"publish FEAT-004 to Jira"
```

Each stage reads the files before it asks you anything, so you can close the chat and come back later.

## `03` — How a feature moves

![Per-item lifecycle: Shape, Spec, Review and Plan; passing checks deliver Markdown, while publication requires a separate request and confirmation.](docs/diagrams/lifecycle.svg)

One feature walks the path after its epic split is accepted. Its siblings mind their own stations: `FEAT-004` can sit in spec while `FEAT-002` already has a plan.

- Ending a chat does not submit a draft or nudge the others along.
- A passing plan hands you the story, the approach, and the tasks.
- Publishing waits for a separate request. A saved Jira preference is not a yes.

Shared helpers for knowledge, trace, lint, status, assets, and visuals live in `skills/_shared/`. Packaging copies what each skill needs into its own folder.

### Back from files, not from memory

The board is rebuilt from saved files: station, condition, blockers, and what you can do next.

- A reserved feature shows up before its story file exists.
- Two candidates means you choose, even when they share a station.
- A stale graph cannot decide the next step for you.
- Step-back and reset keep the files and the IDs.
- Returning to spec retires the active approval and keeps the history. Unchanged text keeps the same hash.
- Published requirements stay published. A change needs a current baseline and a change request.
- New evidence can quote a conflict. Importing it does not rewrite the story.
- An accepted edit gets an exact backup, outside the active scan.

## `04` — House rules

> Traceable changes. Explicit reviews. Deliberate publishing.

- **Published text wins.** Jira is the authority after publication. Local work uses frozen snapshots.
- **One skill may publish.** `sw-publish` is the only writer to Jira or Confluence. It wants a passing plan, active approval, a quality gate, a three-way dry-run, and a fresh yes for that exact plan.
- **Approval is evidence.** `sw-review` records it: a named role, the item, a URL, and a matching hash. Old evidence cannot revive an invalidated approval.
- **Siblings stay put.** Resume one named item. Draft questions stay in spec. Asking about published content does not start a sync.
- **Imports are data.** Documents, issue text, and web pages are not instructions.
- **Lint before hand-off.** Do not weaken a rule to make a check pass.

## `05` — More to read

- [Installation](docs/install.md)
- [Security](docs/security.md)
- [Conventions](docs/conventions.md)
- [Sources](docs/sources.md)
- [Glossary](docs/glossary.md)

## `06` — If you hack on this

Lint first:

```sh
make lint
```

Then the tests, in Docker. The repo is mounted read-only. Git is there for workspace fixtures:

```sh
docker run --rm -v "$PWD:/workspace:ro" -w /workspace python:3.13-slim \
  sh -ec 'apt-get update -qq &&
          apt-get install -y -qq --no-install-recommends git &&
          PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -t .'
```

- The real runtime is `skills/_shared/`. Each skill folder carries a generated copy so it still works alone.
- `tools/vendor.py --write` refreshes those copies. `--check` verifies them.
- Trigger evals are fixtures. They are not a score of model accuracy.
- Publish tests talk to a local Jira mock. They never touch a real Jira site.
- Production use needs a sandbox trial and a human sign-off.

## `07` — License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

<p align="center">
  <sub>SPECWRIGHT · MAKE THE WORK TRACEABLE</sub>
</p>
