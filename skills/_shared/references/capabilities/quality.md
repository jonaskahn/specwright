# Quality capability

Runs deterministic, offline quality gates on front matter, IDs, acceptance criteria,
measurable rules, card shape, sign-offs and generated styles, writing one derived
report.

## Usage

Run _shared/scripts/sw_lint.py with --root <project> and the chosen --gate. Exit 0 means pass;
exit 10, 20 or 30 means the draft, review or publish gate is blocked respectively;
exit 2 is usage or an unexpected checker failure. No network is used.

## Rules

Read each finding as `path:line: L-NNN message`. Choose the gate from
_shared/references/rule-catalog.md. Fix findings through the operation that owns the
artifact, then rerun. Never edit a rule, banned-word list or gate threshold merely to
make a check pass. A waiver, when the gate supports one, is recorded, not invented.
