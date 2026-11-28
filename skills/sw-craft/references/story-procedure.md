# sw-craft — detailed procedure

Load this file only when a step in SKILL.md is unclear, a script exits with an error,
or the case is an edge case named below. SKILL.md is the default path; kernel rules
(`_shared/references/kernel.md`) are not repeated here.

## Procedure

1. Resolve scope before writing: explicit scope, qualified ID, project path, flat
   manifest, otherwise ask. Read existing evidence first. Decide new, resume or amendment
   from files, not memory. An unaccepted idea goes to sw-craft; reserve no FEAT before the
   owner accepts the split (an approver-backed one only under `signoff: required`; see
   `_shared/references/governance.md`). For the chosen item run _shared/scripts/graph.py context and
   read its answered questions, decisions, pending amendments and cited sources first;
   cite with `cite.py stamp`, never retyped quotes.
2. Amendment of published content: start from the latest Jira snapshot obtained through
   normal ingestion, never the stale local draft or an overwritten snapshot. Require a
   real CR-NNN (affected IDs, proposed change, Dev/QA impact). Without both, stop. Name
   the session tool that supplies jira-read or jira-search before its first call, else pasted
   issue content (`_shared/references/capabilities/remote.md`). If reads are unavailable, ask for pasted issue
   content, mark unread fields UNKNOWN and claim no verified baseline. Never write to Jira.
3. Before applying any accepted requirement change, preserve the current artifact with
   `_shared/scripts/record.py backup features/FEAT-NNN/<file>`, then increment its content revision with the real edit.
   Impacts proposed by ingestion never increment revisions.
4. New accepted feature: run scripts/new_story.py --scope-root --scope --summary
   (--feature asserts the expected next ID). It copies assets/jira-story.md (--template
   selects a compatible local one), reserves the next ID across historical scope Markdown
   and refuses overwrite or reuse. A feature reserved earlier (for example from a legacy
   register) is specified with --reserved FEAT-NNN: it keeps its ID, title and aliases.
   Exit 0 created, 1 invalid or conflict, 2 invocation or file error; a warning names any
   open blocking question. Resume an existing draft by editing it, never by reallocating.
5. Collect visual references first: every mockup, Figma link, screenshot or diagram the
   project holds for this feature (asset kinds in `_shared/references/asset-kind.md`).
   Run `_shared/scripts/graph.py neighbors FEAT-NNN --dir in --rel supports`, then the same for
   its epic and idea, and keep the figma, mockup, image and diagram assets. List each ASSET id
   in the `assets:` front matter and in the UI/UX Visuals list (line format in assets/jira-story.md),
   saying which AC or state it shows. Open local images and take UI states from what they show;
   an unclear or missing state becomes a Q record, not an invented state. Quote a link, never
   fetch it. Lint rules L-066 and L-067 check this. Then fill all twelve sections in template
   order; write "None — reason" for intentionally empty ones. Write ACs per
   references/ac-writing.md: at least two with concrete inputs and observable outputs; happy
   path, every rule branch, boundaries, enumerated errors. Write each as a bulleted list with
   the keywords in bold (`- **Given** …`, `- **When** …`, `- **Then** …`; layout in that file). AC IDs stay stable; new
   numbers exceed every number used for this FEAT; withdrawn IDs stay as tombstones, for
   example "~~AC-001-4~~ withdrawn — CR-001".
6. Rules and quality: sentence syntax per references/ears.md; policy per
   references/business-rules.md (key numbers inline, worked example per rule, complete
   decision table for multiple conditions); NFRs per references/nfr-defaults.md (proposed
   thresholds need stakeholder agreement).
7. Illustration, once the criteria exist and before the card. A story that needs a picture gets one,
   drawn as SVG and shown inside the story; a link to a file is not enough. Run
   `scripts/illustration_check.py FEAT-NNN` and act on the chip (definitions in
   references/illustration-need.md):
   - **needs illustration**: draw and embed. Pick a type from references/type-picker.md
     (behaviour-dominant: references/semantic-patterns.md first), read its references/type-*.md
     (a type this build lacks → nearest listed type or a paragraph), write the JSON spec to
     `diagrams/FEAT-NNN.<type>.json` with the story's AC and BR IDs in `spec_ids`, and render
     `scripts/render_diagram.py diagrams/FEAT-NNN.<type>.json diagrams/FEAT-NNN.<type>.svg`
     (exit 3: keep the paragraph; --list-types; contract references/style.md, motion
     references/motion.md). Check the SVG with scripts/check_borders.py and
     scripts/check_offline.py, then
     `scripts/embed_diagram.py FEAT-NNN diagrams/FEAT-NNN.<type>.svg --scope-root <project> --alt "<what it shows, AC ids>"`.
     It lists the picture under UI/UX Visuals, puts the image line under it and restamps the hash.
     At most two pictures per story, each answering a different question. HTML is an optional
     companion for a type whose data table matters, never the only file.
   - **check illustration**: decide now, never hand off in this state. Draw the smallest fitting
     type (flowchart, state or sequence), or dismiss with one line of reason
     (`scripts/illustration_check.py FEAT-NNN --dismiss "reason"`, front matter only, hash stays).
     A picture citing a withdrawn or missing ID is redrawn.
   - **illustrated**: leave the picture, but when the line `not embedded:` appears, run
     `embed_diagram.py` for it. A line `image not found:` means fix the path.
   - **no illustration**: keep the paragraph.
   - **Approved story** (accepted, published or ready-for-dev): draw the picture, never edit the
     story. `embed_diagram.py` refuses (exit 3); report "picture drawn at <path>; embedding changes
     the hash, so it goes through a change request".
   The picture restates the criteria and rules and adds none: a fact that only the drawing shows
   is a defect.
8. Unknowns become Q records (limits and command: `_shared/references/stop-and-ask.md`). Put at
   most three `[NEEDS CLARIFICATION: Q-NNN]` markers in a document, each linked to a real Q. If more uncertainty remains, narrow scope or pause;
    never bury questions in invented "None" values. Unanswered questions stay open; no default
    is written as a rule. Hold dependent work and continue independent items. List unresolved
    Q references in Open questions, including non-blocking questions.
9. Record Dev and QA consumer-check results in the Identity section, not in behaviour. The
   hash field stays inside the level-two Identity section (kitlib hashing excludes that
   whole section and the front matter). Recompute the hash after every body edit with
   `scripts/spec_hash.py --scope-root --stamp FEAT-NNN` (`--check` verifies instead).
10. Card: run scripts/card_gen.py <story> (--stdout previews) from assets/summary-card.md.
    Exit 0 generated, 1 content invalid, 2 invocation or file error. Summary at most 150
    words, whole card at most 80 lines; Goal's first sentence plus key BR numbers, no AC text.
    Generate it once the embedded picture, when there is one, is already in the story.
11. Review prep: read _shared/references/dor.md and run
    `_shared/scripts/sw_lint.py --root <project> --gate review` (exit 20 = blocking findings); fix
    and rerun. After any embed or picture change repeat steps 10 and 11 (regenerate the card, lint); the hash
    is already restamped by embed_diagram.py, so `spec_hash.py --check` confirms it. A proposed amendment blocks the gate
    until it is applied or rejected (`record.py amend apply`). L-064 and L-065 are
    warnings and do not block submission. Stay draft while blocking Qs or error findings
    remain. Do not set in-review by editing the status: the hand-off applies `submit-review`
    through `../sw-start/scripts/transition.py` (the agent passes the token itself under
    `flow: auto`), which refuses while a blocking Q is unanswered. Never set
    ready-to-publish (shown as accepted) or ready-for-dev without sw-craft.
12. Gherkin export, when requested: scripts/export_feature.py <story>.
13. Tasks: write `tasks/FEAT-NNN/FEAT-NNN.tasks.md` (format in `references/task-format.md`). Every new
    task carries `Status: not-started`; `Evidence:` is written only by sw-forge when the code
    elsewhere proves a task done. Coverage is checked by sw-forge, never by an edit of the story's status.
14. Published story: never edit it in place. Open a `CR-NNN` (`assets/cr.md`) with the target's
    `base_hash`, a Delta table, Must not change and the proposed wording; `scripts/merge.py
    base|check` keep it current. A CR that is not applied or rejected blocks nothing in the
    draft, but the edit waits for it.

## Several features

Two or more accepted, reserved features of one scope with no story yet (or several named
drafts) are written in parallel, one sub-agent per FEAT, as the default; offer a single
pick instead. Follow references/parallel-spec.md and _shared/references/parallel-writers.md:
a worker writes only its own `features/FEAT-NNN/FEAT-NNN.*` files; the lead guards the writes with
`_shared/scripts/parallel_guard.py`, then saves questions, trace, lint, graph and data once.
One feature, an amendment of published content, or a host without sub-agents stays serial.

## Consumer check

Dev: per AC, are actor, prerequisites, decision rules, dependencies and failure behaviour
clear enough to begin? QA: can each AC become a test with a concrete input and expected
result, including boundary and error rows? Record yes/no per AC with a reason; any "no"
means revise or open a Q. Prose assertion is not test evidence.

## Stop and ask

Questions follow `_shared/references/stop-and-ask.md`. Stop an amendment without a CR or a current snapshot, and any write with ambiguous scope.
Defaults never resolve conflicting policy or approvals.

## Gotchas

- Parallel workers never touch records, registry, RTM or siblings; the lead does, after the guard passes.
- Jira wins for published story text; a local card is an index, not an authority.
- An over-long card is rejected, not silently accepted.
- Withdrawn AC numbers stay reserved even when their text no longer ships.
- A performance number without load and a measurement method is not a usable NFR.
- Empty Open questions does not imply PO sign-off; evidence must exist.
