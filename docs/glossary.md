# Glossary

| Term | Meaning |
|---|---|
| Epic | `EPIC-NNN`. An optional grouping above features that may span projects. |
| Feature | `FEAT-NNN`. Also called Story by product and QA. One document, one Jira Story. |
| Story | The BA/PO word for a Feature. STORY-001 is an input alias only; files use FEAT-001. |
| Acceptance criterion | `AC-<feature number>-<n>`. A Given/When/Then observable criterion inside a FEAT. |
| Task | `TASK-<feature number>-<n>`. An agent-executable unit in `03-plan/FEAT-NNN.tasks.md`. |
| Spec root | The folder holding `project.yaml` or `workspace.yaml`, either at the repository root or under `.specwright/`. |
| Layout | `docs` (spec root is the repository root) or `embedded` (spec root is `.specwright/` inside a code repository). |
| Program | Several projects sharing one spec root, with `projects/<SCOPE>/project.yaml` per project. |
| Knowledge graph | The derived, committed map under `_meta/graph/` that links every item with provenance. |
