# sankey

## Best for

Quantities splitting and merging.

## Not this type

Use data-flow when quantities are unknown.

## Layout and meaning

Band widths share one quantitative scale; internal incoming and outgoing quantities must balance.
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
  "type": "sankey",
  "title": "Refund example \u00b7 sankey",
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
      "stage": 0
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "stage": 1
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "stage": 1
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "stage": 2
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "stage": 3
    }
  ],
  "edges": [
    {
      "from": "n1",
      "to": "n2",
      "label": "cases",
      "weight": 40
    },
    {
      "from": "n1",
      "to": "n3",
      "label": "cases",
      "weight": 60
    },
    {
      "from": "n2",
      "to": "n4",
      "label": "cases",
      "weight": 40
    },
    {
      "from": "n3",
      "to": "n4",
      "label": "cases",
      "weight": 60
    },
    {
      "from": "n4",
      "to": "n5",
      "label": "cases",
      "weight": 100
    }
  ],
  "unit": "Illustrative cases"
}
```

## Output

Use assets/sankey.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
