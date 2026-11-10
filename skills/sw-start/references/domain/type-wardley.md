# wardley

## Best for

Value chain against evolution.

## Not this type

Use quadrant for generic scoring.

## Layout and meaning

Horizontal evolution and vertical visibility are supplied judgments, not measured maturity.
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
  "type": "wardley",
  "title": "Refund example \u00b7 wardley",
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
      "evolution": 0.1,
      "visibility": 0.9
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "evolution": 0.28,
      "visibility": 0.74
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "evolution": 0.45999999999999996,
      "visibility": 0.5800000000000001
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "evolution": 0.64,
      "visibility": 0.42000000000000004
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "evolution": 0.82,
      "visibility": 0.26
    }
  ],
  "edges": [
    {
      "from": "n1",
      "to": "n2",
      "label": "supplies evidence"
    },
    {
      "from": "n2",
      "to": "n3",
      "label": "supplies evidence"
    },
    {
      "from": "n3",
      "to": "n4",
      "label": "supplies evidence"
    },
    {
      "from": "n4",
      "to": "n5",
      "label": "supplies evidence"
    }
  ]
}
```

## Output

Use assets/wardley.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
