# folder layout

A workspace is one of two layouts, chosen at init.

## docs

The spec root is the repository root. `project.yaml` sits at the root; all scope folders (`00-inbox/`, `01-analysis/`,
`02-drafts/`, `03-plan/`, `assets/`, `diagrams/`,
`records/`, `snapshots/`, `_meta/`) live beside it. Use this for a spec-only repository.

## embedded

The spec root is `.specwright/` inside a code repository; the code lives beside it. The
root code repo holds no `project.yaml` — the manifest lives under `.specwright/`. Use
this when a code repository already exists and specs must not be written outside the
`.specwright/` folder without being asked.

## program

A program is a `workspace.yaml` root listing several scopes under `projects/<SCOPE>/`,
each with its own `project.yaml`. Either layout can host a program; the program manifest
wins over nested project files when resolving a root.
