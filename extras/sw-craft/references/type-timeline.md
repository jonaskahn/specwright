# timeline

## Best for

Dated events and milestones.

## Not this type

Use process when dates are unknown.

## Layout and meaning

Calendar positions are proportional to elapsed days, never evenly spaced for decoration.
Meaning comes from labels, shape, relationships and source IDs, not decoration.
Compare the complete source values below the figure before hand-off.

## Complexity budget

At most 9 items, fourteen connections where applicable, two focal source-linked cards.
Split by business boundary rather than shrink labels. The paragraph gate still
refuses fewer than five items and one actor; never invent an actor to bypass it.

## JSON additions

Common contract: references/style.md. The input below is illustrative and shows every
required field. Source order is kept unless a calendar or parent relation sets position.
Resolve omitted observations; never replace them with policy. Unknown fields are rejected.

```json
{
  "type": "timeline",
  "title": "Refund example \u00b7 timeline",
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
      "date": "2026-01-01"
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "date": "2026-01-04"
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "date": "2026-01-12"
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "date": "2026-02-01"
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "date": "2026-02-05"
    }
  ],
  "edges": []
}
```

## Output

Use assets/timeline.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
A Mermaid companion is emitted; it is editable, not a pixel-identical export.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
