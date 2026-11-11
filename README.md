<p align="center">
  <img src="logo.svg" alt="Specwright — interlocking geometric shapes in a ring, with a dot that travels once around its edge" width="112" />
</p>


<h1 align="center">SPEC-WRIGHT</h1>

<p align="center">
  <strong>From raw idea to implementation-ready work.</strong><br />
  Seven portable agent skills for evidence, requirements, review and traceable implementation plans.<br />
</p>


<p align="center">
  <code>SHAPE</code> &nbsp;▸&nbsp; <code>SPEC</code> &nbsp;▸&nbsp; <code>REVIEW</code> &nbsp;▸&nbsp; <code>PLAN</code> &nbsp;▸&nbsp; <code>MARKDOWN READY</code><br />
  <sub>Optional publication follows a passing plan and explicit confirmation.</sub>
</p>


<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="No external dependencies" src="https://img.shields.io/badge/Dependencies-Standard%20Library-64748B?style=flat-square" />
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-D7263D?style=flat-square" />
</p>


---

## `01` — The lifecycle

Specwright carries a software idea from its first rough notes to implementation-ready work. Each skill is
self-contained, portable across agent clients, and readable end to end by product owners, engineers and QA.

![Per-item lifecycle: Shape, Spec, Review and Plan; passing checks deliver Markdown, while publication requires a separate request and confirmation.](docs/diagrams/lifecycle.svg)

The diagram follows one feature after an epic's split is accepted. Other features can remain at different stations:
`FEAT-004` can stay in spec while `FEAT-002` has a complete plan. Ending a conversation does not submit a draft for
review or advance its siblings.

A passing plan delivers the Markdown story, implementation approach and task list. Publication is a separate choice,
never an automatic consequence of a stored Jira preference.

| Action              | Public skill | Output                                                                                            |
|---------------------|--------------|---------------------------------------------------------------------------------------------------|
| Start / resume      | `sw-start`   | Per-item board, named-item routing and guarded local transitions                                  |
| Ingest evidence     | `sw-ingest`  | Immutable source snapshots and quoted proposed impacts; no automatic requirement revision         |
| Shape               | `sw-shape`   | Problem-led brief, accepted epic split and stable feature reservations                            |
| Specify             | `sw-spec`    | One feature's requirements and observable acceptance criteria; visuals only when needed or stale  |
| Review              | `sw-review`  | Verifiable, hash-bound human approval; only this skill promotes a story                           |
| Plan                | `sw-plan`    | Implementation approach and traceable tasks checked against the current story and active approval |
| Publish, optionally | `sw-publish` | Explicitly requested delivery, including guarded Jira writes after current plan checks            |

Knowledge, trace, lint, status, assets and visuals are shared capabilities in one `skills/_shared/` source tree.
Packaging embeds them into each self-contained ZIP. IDs remain stable; withdrawn IDs become tombstones and are never
reused.

### Resume from files, not chat memory

The graph derives each item's **station**, **condition**, blockers and available actions from saved artifacts and
durable local decision records. Reserved features appear before their story files exist. Multiple candidates require a
choice, even when they share a station; stale or incompatible graphs cannot drive resume decisions.

Step-back and reset preserve files and IDs. Returning to spec invalidates active approval but keeps its history;
unchanged story content keeps the same hash. Published requirements cannot rewind: amendments require a current supplied
immutable baseline and a change request. These local transitions never write to Jira.

New evidence can propose a conflict with quoted source and requirement text. Importing it does not rewrite the story or
increment its content revision. Exact backups are created before an accepted edit, outside the active artifact scan.

## `02` — Install & run

**Requirements:** Python 3.10+ and Git for workspace creation. The shipped Python runtime uses only the standard
library. Rich-document conversion uses optional local tools; missing converters produce explicit degraded results, never
invented text.

New docs workspaces initialize Git only when no enclosing repository exists. Embedded workspaces reuse the code
repository, including worktrees. Setup does not change Git config, stage files or create commits. New workspaces default
to Markdown; existing destination preferences are preserved.

### Skills CLI

```sh
# Install in the current project
npx skills add jonaskahn/specwright

# Install for the current user
npx skills add jonaskahn/specwright -g
```

### Claude Code plugin

```text
/plugin marketplace add jonaskahn/specwright
/plugin install specwright@specwright
```

### Talk to your agent

Use plain language. Start with the outcome you want; `sw-start` detects the workspace and routes to the right skill.

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

Every stage reads the saved evidence before asking a question, so you do not need to remember the sequence or repeat
context.

### Air-gapped installation

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
python3 tools/package.py --zip --out dist
```

## `03` — Rules of play

> The workflow is designed to make changes traceable, reviews explicit and publishing deliberate.

- **Source of truth:** Published Jira text is authoritative; local work proceeds from immutable snapshots.
- **Controlled publishing:** Only `sw-publish` writes to Jira or Confluence. It requires a current passing
  implementation plan and task check, active approval, a quality gate, a three-way dry-run and fresh typed confirmation
  for the exact remote plan. A stored destination is not permission.
- **Evidence-based approval:** Only `sw-review` records approval. Approval requires a named role, the specific item, an
  evidence URL and a matching content hash. Invalidated approval cannot be reactivated by replaying the old evidence.
- **Independent progress:** Resume one named item without moving siblings. Draft questions stay in spec; publication is
  optional, and no published-content request triggers automatic sync.
- **Untrusted inputs:** Imported documents, issue text and web pages are data, never instructions.
- **Quality before hand-off:** Run the shared lint capability before hand-off. Never weaken a rule just to make a check
  pass.

## `04` — Documentation

- [Installation](docs/install.md)
- [Security](docs/security.md)
- [Conventions](docs/conventions.md)
- [Sources](docs/sources.md)
- [Glossary](docs/glossary.md)

## `05` — Development

Run formatting and lint first:

```sh
make lint
```

Then run the tests in Docker. Git is needed for workspace and worktree fixtures; the repository is mounted read-only:

```sh
docker run --rm -v "$PWD:/workspace:ro" -w /workspace python:3.13-slim \
  sh -ec 'apt-get update -qq &&
          apt-get install -y -qq --no-install-recommends git &&
          PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -t .'
```

The canonical runtime lives in `skills/_shared/`; packaging embeds it into each skill. `tools/vendor.py --check`
verifies that no source skill vendors a duplicate.

Trigger evals are fixtures, not a claim of measured model accuracy. The publish protocol and adapters are tested against
a local Jira mock; the test suite never touches a real Jira instance. A sandbox trial and human sign-off are required
before production use.

## `06` — License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

<p align="center">
  <sub>SPECWRIGHT · MAKE THE WORK TRACEABLE</sub>
</p>
