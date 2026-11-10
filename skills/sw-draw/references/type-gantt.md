# gantt

## Best for

Dated work intervals.

## Not this type

Use timeline for isolated milestones.

## Layout and meaning

Interval bars use a shared calendar scale; end dates cannot precede start dates.
Meaning comes from labels, shape, relationships and source IDs, not decoration.
Compare the complete source values below the figure before hand-off.

## Complexity budget

At most 9 items, fourteen connections where applicable, two focal source-linked cards.
Split by business boundary rather than shrink labels. The paragraph gate still
refuses fewer than five items and one actor; never invent an actor to bypass it.

## JSON additions

The common contract in references/style.md applies. This complete illustrative
input shows every required field. Source order is retained unless a calendar or
parent relation determines position. Omitted observations must be resolved, not
silently replaced with policy. Unknown fields are rejected.

```json
{
  "type": "gantt",
  "title": "Refund example \u00b7 gantt",
  "actors": [
    "Customer",
    "Reviewer"
  ],
  "nodes": [
    {
      "id": "n1",
      "label": "Request",
      "spec_ids": [
        "BR-001"
      ],
      "start": "2026-01-01",
      "end": "2026-01-04"
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "start": "2026-01-04",
      "end": "2026-01-07"
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "start": "2026-01-07",
      "end": "2026-01-10"
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "start": "2026-01-10",
      "end": "2026-01-13"
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "start": "2026-01-13",
      "end": "2026-01-16"
    }
  ],
  "edges": []
}
```

## Output

Use assets/gantt.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
A Mermaid companion is emitted; it is editable, not a pixel-identical export.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
