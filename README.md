<p align="center">
  <img src="logo.svg" alt="Specwright — interlocking geometric shapes in a ring, with a dot that travels once around its edge" width="104" />
</p>
<h2 align="center">SPEC·WRIGHT</h2>
<p align="center">
  <strong>A rough idea goes in. A story, a plan and a task list come out.</strong><br />
  Five agent skills. Every step a file you can read, diff and commit.
</p>
<p align="center">
  <code>IDEA</code> ▸ <code>SHAPE</code> ▸ <code>SPEC</code> ▸ <code>REVIEW</code> ▸ <code>PLAN</code> ▸ <code>PROMPTS</code>
</p>
<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="Standard library only" src="https://img.shields.io/badge/Dependencies-Standard%20Library-64748B?style=flat-square" />
  <img alt="Five skills" src="https://img.shields.io/badge/Skills-5-D7263D?style=flat-square" />
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-D7263D?style=flat-square" />
</p>

---

## `01` ▸ QUICK START

```sh
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh
```

<p align="center">
  <img src="docs/diagrams/chat-session.svg" alt="A chat thread: the person asks for a refunds spec; sw-start reports the workspace and asks three prefilled questions; sw-craft freezes the policy snapshot, proposes FEAT-001 and FEAT-002, records the accepted story at hash 7c1a9f3d2e41 and says forge to continue." width="920" />
</p>

Three prefilled questions on a first run. After that the stations hand off on their own and stop only
for a person: accept the split, accept the story, answer a blocking question.

**Everything is a file.** Open it, diff it, commit it, hand it to someone else:

```text
┌─ WHERE IT LANDS ───────────────────────────────────────────── FILE MAP ┐
│  your-repo/   or   your-repo/.specwright/                              │
│  00-inbox/      frozen sources      SRC-0001--policy.md                │
│  01-analysis/   problem, evidence   BO-001 · IDEA-refunds              │
│  02-drafts/     what to build       FEAT-001.story.md                  │
│  03-plan/       the work            FEAT-001.tasks.md                  │
│    prompts/     one per session     TASK-001-1.md                      │
│  records/       decisions           Q-001 · DEC-001 · CR-001           │
│  diagrams/      pictures            FEAT-001.swimlane.svg              │
│  _meta/         start here          READ-FIRST.md                      │
└────────────────────────────────────────────────────────────────────────┘
```

A new chat reads `_meta/READ-FIRST.md` and carries on. Nothing depends on remembering this one.

---

## `02` ▸ THE COMMANDS

Say what you want in plain words. Slash commands are shortcuts; an agent that hears no command
loads `sw-start` first and routes from there. `/sw-continue` resumes from wherever the work stands.

| Command | Role | Turns | Into |
| --- | --- | --- | --- |
| `sw-start` | the door | any request | the right skill, or the board |
| `sw-craft` | BA | idea, document, live system | an accepted story, criteria, tasks, diagrams |
| `sw-forge` | Dev | an accepted story | a file-level plan, one prompt per task |
| `sw-ship` | publish | an accepted story | Jira items, behind a fresh yes |
| `sw-view` | see | the files | a read-only console |

Two roles, five skills. The BA and the Dev may be different people — then one word switches over.
One feature walks the rail after its epic split is accepted; its siblings mind their own stations,
so `FEAT-004` can sit in spec while `FEAT-002` already has a plan.

```text
┌─ THE RAIL ────────────────────────────────────────────── AUTO HAND-OFF ┐
│  STATION      PRODUCES                        WAITS FOR                │
├────────────────────────────────────────────────────────────────────────┤
│  [1] SHAPE    problem, non-goals, the split   accept the split         │
│  [2] SPEC     criteria, rules, NFRs, tasks    accept the story         │
│  [3] REVIEW   3 reviewers, a pack, disputes   your plain yes           │
│  [4] PLAN     files, the change, the test     hand to a coder          │
│  [5] SHIP     Jira epics, stories, tasks      a fresh yes              │
└────────────────────────────────────────────────────────────────────────┘
```

<p align="center">
  <img src="docs/diagrams/lifecycle.svg" alt="Per-item lifecycle: Shape, Spec and Review advance on saved evidence; the owner says forge to start Plan, which delivers Markdown; publication branches from the accepted story on an explicit request and a fresh confirmation." width="920" />
</p>

### `sw-start` · the door

<p align="center">
  <img src="docs/diagrams/chat-start.svg" alt="A chat thread: the person resumes REF:FEAT-004; sw-start reports that FEAT-004 is in review and FEAT-002 is accepted with no plan, then moves only the named item." width="920" />
</p>

| You want | Say |
| --- | --- |
| Start in a repo with an idea | `start a spec for the refunds flow` |
| Know what the kit can do | `what can you do?` |
| Pick up old work | `resume REF:FEAT-004` |
| See the board for an epic | `show the board for EPIC-001` |
| Pin the tech stack | `lock the stack` |
| Keep the run moving | `continue` |

Reads the build files (Maven, Gradle, npm, Python, Go, Flutter, .NET, compose, Terraform) and
proposes a stack profile. You lock it once, bound to the profile's hash. Stories stay
technology-free; every code task carries a `Stack:` line, and a task outside the lock stops the run.

A new project with no code gets one **foundation story** first: structure, format, lint, tests with a
coverage floor, one `make check`, CI and an `AGENTS.md`. Up to five prefilled questions.

### `sw-craft` · the BA line

`INTAKE ▸ AS-IS ▸ SHAPE ▸ STORY ▸ REVIEW`

<p align="center">
  <img src="docs/diagrams/chat-craft.svg" alt="A chat thread: the person asks what refunds do today; sw-craft reports four criteria across six files and offers version 1 plus a fix." width="920" />
</p>

- **Shape** an idea into a problem-led brief and an INVEST split.
- **Import** documents, exports, emails and Jira text as frozen, cited snapshots.
- **Analyse** a live system into a gap table, criterion by criterion.
- **Write** the story: criteria, rules, NFRs, diagrams, then the task breakdown.
- **Review** with three independent reviewers, then one accept.

What a story carries: a problem-led goal, at least two Given/When/Then criteria with real values,
business rules with a worked example, measurable NFRs, a diagram when it helps, and tasks traced to
criteria with a layer, a test command and a "stop and ask if" line.

For something already built, `analyse` writes a gap table — what the feature should do against what
code and tests do today, each citation going stale when the code changes:

```text
┌─ A GAP TABLE ─────────────────────────────────────────────────── AS-IS ┐
│  done       refund within the first 7 days                             │
│             CODE:api/refund.py:L41-L58#9f2c1a4b                        │
│  partial    half refund between days 8 and 14                          │
│             CODE:api/refund.py:L61-L70#4b8d2e0f                        │
│  missing    refuse a request after day 14                              │
│             no handler in the code root                                │
│  divergent  one audit row per request                                  │
│             CODE:api/audit.py:L9-L22#c31a7f92                          │
└────────────────────────────────────────────────────────────────────────┘
```

The gaps decide the shape: nothing built → a new story; all done → version 1 of the live feature;
some gaps → version 1 plus a completion change; code wrong → a fix.

**Approval is bound to the text.** Edit the story after your accept and the approval goes stale by
itself. Old evidence cannot revive it.

### `sw-forge` · the Dev plan

<p align="center">
  <img src="docs/diagrams/chat-forge.svg" alt="A chat thread: the person asks to plan FEAT-004; sw-forge asks for a stack lock, then writes a four-section plan and one prompt per task." width="920" />
</p>

An accepted story becomes a plan detailed enough to apply without judgement, then one self-contained
prompt per task. No code is written here, and no code root is touched.

| Start from | Say | Lands on disk |
| --- | --- | --- |
| An accepted story | `plan FEAT-004` | `03-plan/FEAT-004.plan.md` |
| The finished plan | *(automatic)* | `03-plan/prompts/FEAT-004/TASK-004-1.md` + `_order.md` |
| Real work | `TASK-004-1 is done — make test: 42 passed` | status and evidence in `FEAT-004.tasks.md` |

Each plan section names the exact files, the change itself, the test that proves it, the command
that runs it, the order against other tasks, and the condition under which a coder must stop.

```text
┌─ TASK STATUS ────────────────────────────────────────────── REAL STATE ┐
│  planned       the plan section exists                                 │
│  in-progress   a coder started it                                      │
│  done          evidence: command, result, exit code                    │
│  blocked       a reason: what is missing                               │
└────────────────────────────────────────────────────────────────────────┘
```

A story never reaches `done` while a task is open or a criterion has no evidence. Hand `_order.md`
and the prompts to Claude Code or another agent, **one task per session**.

### `sw-ship` · publish, on request

<p align="center">
  <img src="docs/diagrams/chat-ship.svg" alt="A chat thread: the person asks to publish FEAT-004 to Jira; sw-ship asks which level and requires a fresh yes to the exact dry-run plan." width="920" />
</p>

The only skill that writes to Jira. It never runs on its own.

```text
┌─ THE DRY RUN ─────────────────────────────────────────────── THREE-WAY ┐
│  level?   epic only · story only · tasks only · all three              │
│           default: story only                                          │
├────────────────────────────────────────────────────────────────────────┤
│  EPIC-001    →  create (Epic)                                          │
│  FEAT-004    →  update (Story, hash 7c1a9f3d2e41)                      │
│  TASK-004-1  →  create (Sub-task of PROJ-123)                          │
│  TASK-004-2  →  create (Sub-task of PROJ-123)                          │
├────────────────────────────────────────────────────────────────────────┤
│  a fresh yes to this exact plan, then                                  │
│  PUBLISH REF:FEAT-004 7c1a9f3d                                         │
└────────────────────────────────────────────────────────────────────────┘
```

A saved preference is not permission; a remembered yes is not a yes. No deletes, no forced
transitions, and an ambiguous create is checked on the remote before anything is retried. When Jira
runs ahead of the files, that is reported as drift, never pulled back.

### `sw-view` · see the state

<p align="center">
  <img src="docs/diagrams/chat-view.svg" alt="A chat thread: the person asks to open the console; sw-view reports Node and fresh data and serves on 127.0.0.1:4173." width="920" />
</p>

A local, read-only console. It writes nothing but its own git-ignored build folder, needs Node 24+
(offered once, installed only after a yes) and serves on `127.0.0.1`.

| Screen | Answers |
| --- | --- |
| Overview | What needs a person, right now |
| Features | Every story, its station, its acceptance |
| Tasks | Real task status, with evidence |
| Board | Epic swimlanes, one column per task status |
| Graph | Trace, network, table and outline views |
| Records | Questions, decisions, change requests |
| Quality | Lint and drift, per item |

---

## `03` ▸ INSTALL

### macOS and Linux

```sh
# every project
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh

# this project only
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --project

# named agents, no questions
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --agent cursor --agent claude-code -y

# a release, or a branch
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --version 0.9.0
curl -fsSL https://raw.githubusercontent.com/jonaskahn/specwright/main/install.sh | sh -s -- --branch v0.9
```

### Windows

```powershell
irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1 | iex
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Project
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Agent cursor,claude-code -Yes
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/jonaskahn/specwright/main/install.ps1))) -Version 0.9.0 -Yes
```

### `npx`, plugin, air-gapped

```sh
npx skills add jonaskahn/specwright -g     # every project
npx skills add jonaskahn/specwright        # this project
python3 workshop/tools/install.py --target /absolute/path/to/spec-repo
python3 workshop/tools/package.py --zip --out dist
```

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

`npx` and the plugin read `skills/` from the repo, all 45 diagram types included. ZIP builds default
to the 10 core types. The offline installer also writes the project instruction files.

### Upgrading

From the unzipped new kit:

```sh
sh migrate.sh --dry-run ~/.claude/skills     # see the plan
sh migrate.sh ~/.claude/skills               # replace old sw-* skills, back them up beside it
sh migrate.sh /path/to/your/kit-checkout     # replace kit folders; workshop/ and tests stay
sh migrate.sh --flow-auto /path/to/spec-repo # refresh AGENTS.md, switch to automatic hand-off
```

It detects the target kind, refuses a folder that is not Specwright, and never deletes spec work.

### Where the spec lives

The spec root is always `.specwright/` in the repository. It holds one project, or a program with
`projects/<SCOPE>/` for several.

A new workspace starts a Git repo only when the folder is not already inside one. It reuses an
existing repo, worktrees included. Setup changes no Git config and stages no files.

### Runtimes

- **To install the skills:** `curl`, `irm` or `npx`. No Node, no Python.
- **To run them:** Python 3.10+ and Git. The standard library is enough. A shell script checks for
  Python without needing it, and offers the install command.
- **For `sw-view`:** Node 24+, offered once, installed only after a yes.
- **Richer documents:** optional local tools such as pandoc. A missing tool says so; it never
  invents the document.

The full matrix — offline mirrors, archives and verification — is in
[docs/install.md](docs/install.md).

---

## `04` ▸ HOUSE RULES

> Traceable changes. Explicit reviews. Deliberate publishing.

- **Published text wins.** Jira is the authority after publication. Local work uses frozen snapshots.
- **One skill may publish.** `sw-ship`, with an accepted story, a quality gate, a three-way dry-run
  and a fresh yes for that exact plan.
- **Every command ends with a git checkpoint.** The spec files a command changed are committed
  (`<skill>: <what changed>`) and, with a remote, pushed: never forced, never past a failing hook,
  never touching your other work. Set `checkpoint: commit` or `off` in the manifest to stop.
- **Approval is bound to the content.** A plain accept with the matching hash, or under
  `signoff: required` a named role, item, URL and matching hash.
- **Named items move alone.** `resume FEAT-004` moves only FEAT-004; `continue` moves the whole
  scope, station by station.
- **Imports are data.** Documents, issue text and web pages are never instructions. No secrets.
- **Lint before hand-off.** Never weaken a rule to make a check pass.

---

## `05` ▸ IF YOU HACK ON THIS

```sh
make lint
```

Then the tests, in Docker. The repo is mounted read-only; Git is there for workspace fixtures:

```sh
docker run --rm -v "$PWD:/workspace:ro" -w /workspace python:3.13-slim \
  sh -ec 'apt-get update -qq &&
          apt-get install -y -qq --no-install-recommends git &&
          PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s workshop/tests -t workshop &&
          PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests'
```

`make test` runs the same suite locally.

- The real runtime is `skills/_shared/`. Each skill folder carries a generated copy so it works
  alone. `workshop/tools/vendor.py --write` refreshes those copies; `--check` verifies them.
- Two test roots, both run above: `workshop/tests` is the toolkit suite; `tests/` covers the skill
  libraries (`analyze`, `foundation`, `handoff`, `review_merge`, `ship_sync`, `stack_style`).
- Trigger evals are fixtures, not a score of model accuracy.
- Publish tests talk to a local Jira mock. They never touch a real Jira site.
- Production use needs a sandbox trial and a human sign-off.

---

## `06` ▸ MORE

- [Installation](docs/install.md)
- [Security](docs/security.md)
- [Conventions](docs/conventions.md)
- [Sources](docs/sources.md)
- [Glossary](docs/glossary.md)

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

<p align="center">
  <sub>SPECWRIGHT · MAKE THE WORK TRACEABLE</sub>
</p>
