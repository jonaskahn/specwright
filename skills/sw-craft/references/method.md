# Analysis method

## Two views per criterion
- Intended: what it should do. Sources: SRC snapshots (docs, Confluence, other systems), Jira
  keys, the owner's words (`owner`). Code-only behaviour: `observed`.
- Actual: what code and tests do now. Only `CODE:` citations from `analyze.py cite`.
- Code and documents weigh the same. Never pick a winner; a disagreement is `divergent` plus a
  Conflicts line (`Q-NNN` when the feature has an ID, else `ASK-n`) quoting both sides.

## Reading order (token budget)
1. `area` output only; never browse the tree.
2. Docs and tickets for intended criteria (headings, rules, numbers).
3. Entry point (route/screen) → handler → service → data access. Stop at the first file that
   decides the behaviour; cite those lines.
4. Tests: a passing-test name plus assertion is the strongest evidence. Cite the assertion lines.
5. Config and flags that switch behaviour (feature flags, env defaults): cite them.

## One row = one observable behaviour
Concrete values, actor, input, output. "Refund allowed ≤ 30 days after payment", not
"refund rules". Split a row when code handles two cases differently.

## Status
| Status | Meaning |
| --- | --- |
| done | code (and ideally a test) does what is intended |
| partial | some cases or layers exist (API without UI, happy path without errors) |
| missing | intended, no code found in the registered roots |
| divergent | code and intended disagree (values, rules, flow) |
| unknown | cannot tell from what was read; say what would settle it in Notes |

## Confidence
high: test or two independent code sites agree · medium: one code site, no test · low:
inferred from names, dead code, flags off, or unread branches.

## Auto-accept rule
`done` + `high` + (a test cite or ≥ 2 code cites) is accepted without asking. Every other row
is confirmed by the user in one batch at the stop.

## Shapes (from `check`)
| Shape | Next in sw-craft |
| --- | --- |
| new | new story; nothing is built |
| as-is | confirmed rows become the feature's version 1; then a change if requested |
| complete | version 1 from done rows + a completion change for partial/missing rows |
| fix | after the owner says code is wrong: a fix item; spec wrong: a spec correction |
| mixed | answer questions first, then version 1 + completion change |

## Not covered
List roots, folders or sources not read and why. An unread area is not "missing".
