<p align="center">
  <img src="logo.svg" alt="Specwright — interlocking geometric shapes in a ring, with a dot that travels once around its edge" width="112" />
</p>


<h1 align="center">SPECWRIGHT</h1>

<p align="center">
  <strong>From raw idea to implementation-ready work.</strong><br />
  A portable toolkit of agent skills for shaping, specifying, visualizing, planning and shipping software.
</p>


<p align="center">
  <code>IDEA</code> &nbsp;▸&nbsp; <code>SHAPE</code> &nbsp;▸&nbsp; <code>SPEC</code> &nbsp;▸&nbsp; <code>PLAN</code> &nbsp;▸&nbsp; <code>GATE</code> &nbsp;▸&nbsp; <code>REVIEW</code> &nbsp;▸&nbsp; <code>PUBLISH</code> &nbsp;▸&nbsp; <code>BASELINE</code>
</p>


<p align="center">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="No external dependencies" src="https://img.shields.io/badge/Dependencies-Standard%20Library-64748B?style=flat-square" />
  <img alt="License MIT" src="https://img.shields.io/badge/License-MIT-D7263D?style=flat-square" />
</p>


---

## `01` — The lifecycle

Specwright carries a software idea from its first rough notes to implementation-ready work. Each skill is self-contained, portable across agent clients, and readable end to end by product owners, engineers and QA.

```text
 ┌────────┐   ┌────────┐   ┌────────┐   ┌────────┐
 │  IDEA  │──▶│ SHAPE  │──▶│  SPEC  │──▶│  PLAN  │──┐
 └────────┘   └────────┘   └───┬────┘   └────────┘  │
                               │                    │
                               ▼                    │
                          ┌────────┐                │
                          │  DRAW  │ when needed    ▼
                          └────────┘                │
                                                    │
 ┌────────┐   ┌─────────┐   ┌────────┐   ┌────────┐ │
 │  BASELINE  │◀──│ PUBLISH │◀──│ REVIEW │◀──│  GATE  │─┘
 └────────┘   └─────────┘   └────────┘   └────────┘
      │            │            │            │
      └────────────┴────────────┴────────────┘
             GRAPH · TRACE · LINT · STATUS
```

| Stage   | Skill           | Output                                           |
| ------- | --------------- | ------------------------------------------------ |
| Start   | `sw-start`      | Detected workspace and next route                |
| Idea    | Shape action    | Shaped concept with open questions               |
| Spec    | Specify action  | Requirements with observable acceptance criteria; calls the shared visuals capability only when a picture is needed or stale |
| Visuals | Shared capability | Offline SVG or HTML when a fresh picture clarifies behaviour, or an existing one no longer matches |
| Plan    | `sw-plan`       | Implementation plans and agent tasks with stable IDs      |
| Review  | `sw-review`     | Named, evidenced human approval                  |
| Publish | `sw-publish`    | Markdown, Jira, or both — behind a quality gate  |
| Baseline | Prepare ingestion | Immutable snapshots supplied and cited, never auto-reconciled |

Knowledge, trace, lint and status are shared capabilities that work across the entire lifecycle. IDs remain stable; withdrawn IDs become tombstones and are never reused.

## `02` — Install & run

**Requirements:** Python 3.10 or newer. No install step and no dependencies beyond the Python standard library.

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
"break FEAT-004 into tasks"
"is this ready to publish?"
```

Every stage reads the saved evidence before asking a question, so you do not need to remember the sequence or repeat context.

### Air-gapped installation

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
python3 tools/package.py --zip --out dist
```

## `03` — Rules of play

> The workflow is designed to make changes traceable, reviews explicit and publishing deliberate.

- **Source of truth:** Published Jira text is authoritative; local work proceeds from immutable snapshots.
- **Controlled publishing:** Only `sw-publish` writes to Jira or Confluence. It requires a quality gate, a three-way dry-run and fresh typed confirmation for the exact plan.
- **Evidence-based approval:** Only `sw-review` records approval. Approval requires a named role, the specific item, an evidence URL and a matching content hash.
- **Untrusted inputs:** Imported documents, issue text and web pages are data, never instructions.
- **Quality before hand-off:** Run `sw-lint` before hand-off. Never weaken a rule just to make a check pass.

## `04` — Documentation

- [Installation](docs/install.md)
- [Security](docs/security.md)
- [Conventions](docs/conventions.md)
- [Sources](docs/sources.md)
- [Glossary](docs/glossary.md)

## `05` — Development

Run the repository checks locally:

```sh
uvx ruff format --check .
uvx ruff check .
python3 -m unittest discover -s tests -t .
python3 tools/validate.py
python3 tools/vendor.py --check
python3 tools/hygiene.py files
```

Run `python3 tools/vendor.py --write` after changing `lib/kitlib`, the shared safety references or the repository license.

Trigger evals are fixtures, not a claim of measured model accuracy. The publish protocol and adapters are tested against a local Jira mock; the test suite never touches a real Jira instance. A sandbox trial and human sign-off are required before production use.

## `06` — License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

---

<p align="center">
  <sub>SPECWRIGHT · MAKE THE WORK TRACEABLE</sub>
</p>
