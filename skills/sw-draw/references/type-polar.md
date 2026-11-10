# polar

## Best for

A cyclic category with quantitative magnitude.

## Not this type

Use radar for multi-series criteria.

## Layout and meaning

Angle is category, radial distance is magnitude on a shared maximum.
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
  "type": "polar",
  "title": "Refund example \u00b7 polar",
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
      "value": 12
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "value": 24
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "value": 18
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "value": 30
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "value": 16
    }
  ],
  "edges": [],
  "unit": "Illustrative cases",
  "maximum": 40
}
```

## Output

Use assets/polar.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
