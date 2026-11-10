# Layouts

The spec root is the folder that holds project.yaml or workspace.yaml. All paths are relative to it.

## Embedded in a code repository

The spec root is .specwright/ inside the code repository. One project: project.yaml with code set to ".". Several
projects: workspace.yaml plus projects/<SCOPE>/project.yaml, each with an optional code folder such as services/orders.

## Docs only

The spec root is the repository root, as before. No code key.

## Programs

Several projects share one spec root, either docs-only or embedded in a monorepo. Qualified IDs such as REF:EPIC-001
link projects.

## Choosing

- Default to embedded when the folder holds source files and a git repository.
- Default to docs-only otherwise.
- Never convert a layout automatically; moving the spec root is a manual change.
- In an embedded install, the standing rules are added to an existing AGENTS.md only with the explicit merge option and
  a yes.
- Every project has an assets/ folder for user-provided references; the assets capability writes there.
