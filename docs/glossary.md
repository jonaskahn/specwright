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
| Alias | Another name an item goes by: a legacy ID, a remote page ID, a tracker key, a former title. `graph.py show <alias>` finds the record. |
| Master index | `_meta/INDEX.md` and `index.tsv`: one generated row per artifact (name, aliases, origin, status, parent, links). Never edited by hand. |
| Crosswalk | `_meta/CROSSWALK.tsv`: every legacy or external item mapped to its internal key, with unmatched items listed on both sides. |
| Baseline | An existing set of capabilities the business already runs under its own IDs, imported as a legacy register and shaped into features. |
| Batch | One bulk import. Its manifest (`00-inbox/imports/<batch>/manifest.json`) records expected and received counts and a status per item. |
| Candidate | A claim a worker extracted from a snapshot, with a citation. It is unverified until `candidates.py check` passes and a person reviews it. |
| Citation | `SRC-0001:L12-L14#a1b2`: lines of a saved snapshot plus a hash of the quoted text, checked by `cite.py verify`. |
| Amendment | `AMD-NNN`. A tracked wording change an answered question implies; it blocks the review gate until applied or rejected. |
| Provenance amendment | An attributed correction of a snapshot's source, version or URL, recorded beside the snapshot, which stays untouched. |
