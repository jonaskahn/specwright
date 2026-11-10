# fishbone

## Best for
Hypotheses grouped around an observed effect.

## Not this type
Use dependency for established relations.

## Layout and meaning
Category branches converge on an effect; causes remain hypotheses until independently verified.
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
  "type": "fishbone",
  "title": "Refund example \u00b7 fishbone",
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
      "category": "People"
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "category": "Policy"
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "category": "Process"
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "category": "Tools"
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "category": "Data"
    }
  ],
  "edges": [],
  "effect": "Refund delayed"
}
```

## Output
Use assets/fishbone.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns
Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
