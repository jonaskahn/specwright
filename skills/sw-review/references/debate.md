# Independent review (debate)

Goal: the owner finalizes with understanding, after the draft survived people who did not
write it. Reviewers find problems; the author defends or fixes; disputes reach the owner.

## Independence
- Best: three subagents (Claude Code Task/agents, or any host that starts a fresh context),
  each given only `review/FEAT-NNN.brief.md`. Record `independence: subagent`.
- No subagents (chat): run each role as its own pass, re-reading only the brief's files and
  ignoring your authoring reasoning. Record `independence: same-session`; the pack shows it.

## Roles
| Role | Asks |
| --- | --- |
| critic | Is anything ambiguous, contradictory, unsupported by sources, or out of scope? |
| builder | Where would I have to guess to build it (data, states, errors, limits, existing code)? |
| tester | Can I write one pass and one fail test per AC from the text alone? |

For a change or fix, all roles also read the target story and the analysis: regression
guards, delta correctness, migration of existing data.

## Severity
blocker: build or test would go wrong or stall · major: likely rework or a wrong edge case ·
minor: clarity only. At most 8 findings per role, most severe first, each with evidence.

## Author responses
| Response | Resolution must hold |
| --- | --- |
| accepted | the fix made in the draft (one line) |
| rebutted | evidence: AC/BR/NFR ID, SRC or CODE cite, or quoted line |
| open | Q-NNN (saved with record.py) or `owner` |

## Rounds
1. Reviewers raise findings. 2. Author answers; fixes edit the draft. 3. Reviewers mark each
rebuttal `holds` or `withdrawn` in Resolution; no new findings. Then `debate.py seal`.
Two rounds at most; anything still held or open goes to the owner in the pack.

## Finalizable
`debate.py check` passes when every row is valid, accepted fixes are sealed to the current hash,
the draft did not change after review, and no blocker is open. Held majors and open items do
not block: the owner sees them and decides.
