# Layered writing: epics, then features, then tasks

Write one layer completely before the next, so every link has a target when it is written.
Run this order whenever the work is more than one feature.

## Order

1. **Epics.** Create every epic first (`scripts/new_epic.py`). When one epic needs another to be
   done first, set `depends_on: [EPIC-001]` in its front matter. State the link once, on the
   dependent epic; the reverse link is generated.
2. **Features.** Reserve and write each feature under its epic. A feature that needs another
   feature's result sets `depends_on: [FEAT-001]`. Features with no link between them are
   independent: write them in parallel (`references/parallel-spec.md`). A feature with a link
   waits until its target has a story.
3. **Tasks.** Write each feature's tasks file. A task that needs another task sets
   `Depends on: TASK-001-1`. Independent features' task files are written in parallel; one
   feature's tasks are written by one writer so numbers and links stay consistent.

The first feature of a new project is Foundation (`_shared/scripts/foundation.py`): tooling,
lint, format, tests and the standing rules. Foundation is a hard gate, not just a convention:
`graph.py ready` blocks every feature whose `code:` is not `false` until the project's
foundation feature is done. A documentation-only feature sets `code: false` and starts at once.
Set `kind: foundation` in the foundation story's front matter; a project has one.

## Which work can run in parallel

Ask the graph, never memory: `_shared/scripts/graph.py ready --kind feat` lists the features
with no unfinished `depends_on`. Those are the batch for one parallel round. Run
`graph.py ready --all` to see what blocks the rest.

## After each layer

`_shared/scripts/finish.py` rebuilds the graph and reports `newly_ready`: the items whose last
blocker just finished. Start those next. Finishing an item never approves anything and never
moves work from the BA to the Dev role.

## Status

Delivery status is `todo`, `in_progress` or `done`. Tasks carry it in their `Status:` line;
a feature and an epic roll it up from their children. Blocked is calculated from `depends_on`,
never written down.
