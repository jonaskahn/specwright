# quadrant

## Best for
Positioning against two normalized criteria.

## Not this type
Use scatter for continuous observations.

## Layout and meaning
Coordinates lie on two explicitly named 0–1 axes; crossing lines mark the midpoints.
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
  "type": "quadrant",
  "title": "Refund example \u00b7 quadrant",
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
      "x": 0.1,
      "y": 0.8
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "x": 0.35,
      "y": 0.2
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "x": 0.55,
      "y": 0.7
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "x": 0.75,
      "y": 0.4
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "x": 0.9,
      "y": 0.9
    }
  ],
  "edges": [],
  "x_axis": "Effort",
  "y_axis": "Value"
}
```

## Output
Use assets/quadrant.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
A Mermaid companion is emitted; it is editable, not a pixel-identical export.

## Anti-patterns
Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
