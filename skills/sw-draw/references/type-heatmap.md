# heatmap

## Best for
A bounded row/column intensity matrix.

## Not this type
Use DP security matrix for permissions.

## Layout and meaning
Every cell shows its numeric value; category names and source values remain readable without colour.
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
  "type": "heatmap",
  "title": "Refund example \u00b7 heatmap",
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
      "row": "Read",
      "column": "Policy",
      "value": 1
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "row": "Review",
      "column": "Draft",
      "value": 2
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "row": "Read",
      "column": "Evidence",
      "value": 3
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "row": "Review",
      "column": "Policy",
      "value": 4
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "row": "Read",
      "column": "Draft",
      "value": 5
    }
  ],
  "edges": [],
  "unit": "Illustrative cases",
  "columns": [
    "Policy",
    "Draft",
    "Evidence"
  ],
  "rows": [
    "Read",
    "Review"
  ]
}
```

## Output
Use assets/heatmap.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns
Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
