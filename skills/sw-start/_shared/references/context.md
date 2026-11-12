# Shared context

Specwright turns a software idea into implementation-ready work through seven public
skills. A story (BA/PO word) and a feature (Dev/QA word) are the same item, written
FEAT-NNN; never create a STORY identifier.

## Skills and owners

| Skill | Owns |
| --- | --- |
| sw-start | Detection, routing, workspace setup, guarded transitions, completion maintenance. |
| sw-ingest | Source snapshots, assets, candidate facts, conflicts. |
| sw-shape | Idea brief, INVEST feature split, FEAT reservation. |
| sw-spec | Story drafts, cards, diagrams, RTM draft columns. |
| sw-review | The only recorder of approval: the owner's accept, or a formal sign-off. |
| sw-plan | Implementation plan and tasks. |
| sw-publish | The only writer to Jira or Confluence. |

Knowledge, trace, lint, status, assets and visuals are shared capabilities (see
bundle-map.json); they are not stations.

Governance (optional or required sign-off, guided or step flow, Markdown or Jira) is set in
the manifest; `governance.md` is the one table of what each setting allows.

## Read order

1. sw-start/SKILL.md, then safety.md.
2. Route: the output of sw-start's `scripts/start.py` and its `references/routing.md`.
3. Work: the routed skill's SKILL.md and the references it names.
4. Finish: completion.md, then next-step-table.md; stop at the next human decision.

## Terms

Keep IDs stable. Withdrawn IDs remain tombstones; their numbers are never reused. Store
external key mappings in the ID registry. Use qualified IDs (`SCOPE:FEAT-NNN`) across projects.
