# Conventions

These rules apply to every file in the kit.

## Skills

- One folder per skill under `skills/`, named `sw-<name>`, containing `SKILL.md` and optional
  `references/`, `scripts/` and `assets/`.
- Front matter holds only `name`, `description`, `license` (an SPDX id), `compatibility` and
  `metadata`. Put safety rules in the body, never in vendor-specific keys.
- The description is one line of at most 900 characters in four parts: what the skill does, when
  to use it with real trigger phrases, and a closing "Do NOT use for ... (use sw-x)" clause.
- The body stays under 500 lines and about 5000 tokens. Move detail into `references/` and say
  exactly when to read each file ("When L-009 fires, read references/banned-words.md").
- Body sections, in order: Purpose, Reads and writes, Procedure, Consumer check, Stop and ask,
  Gotchas, Hand-off, Untrusted content, References. Keep gotchas in the body because the agent
  will not know to open a reference for them.
- Test prompts never appear in the body. They live in `evals/<skill>/`:
  - `triggers.jsonl`: rows of `{"query": ..., "should_trigger": true|false}`, at least 8 of each
    kind. Negatives are near misses that belong to a sibling skill (`"near_miss_of": "sw-x"`).
  - `cases.json`: `{"skill": ..., "cases": [{"id", "prompt", "fixture", "assertions"}]}` for
    agent-level checks. Deterministic behaviour is covered by unit tests in `tests/`.
- Jira access is described by capability (read an issue, search by JQL, write an issue), never
  by a vendor tool name. The skill says: use whichever tool in this session provides the
  capability, name it before the first call, and fall back to the bundled REST script. If a read
  capability is missing, ask the user to paste the issue and mark unread fields UNKNOWN. If the
  write capability is missing, stop after the dry-run.

## Scripts

- Standard library only, offline except the explicit Jira REST adapter, Python 3.10+.
- Every script has `--help`, never prompts, prints data on stdout and diagnostics on stderr, and
  uses distinct documented exit codes.
- External programs run with a list argv, no shell, and a timeout.
- Scripts locate the shared library with this bootstrap, so they work from the kit tree and
  from a packaged skill that carries its own copy:

  ```python
  import sys
  from pathlib import Path

  _here = Path(__file__).resolve().parent
  for _base in (_here, *_here.parents):
      if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
          sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
          break
  ```

## Writing style

- Comments say why, in plain words. They never mention work-tracking labels, tickets or tools
  that helped write the code. Product identifiers such as `L-024` and `FEAT-001` are fine.
- Commit subjects are imperative, at most 72 characters, and describe what the change does.
  No trailers.
- Before committing run `uvx ruff check .`, `uvx ruff format --check .`,
  `python3 -m unittest discover -s tests -t .`, `python3 tools/validate.py` and
  `python3 tools/hygiene.py files`.
