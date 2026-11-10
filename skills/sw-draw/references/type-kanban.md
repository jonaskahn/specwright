# kanban

## Best for

A snapshot of work and WIP limits.

## Not this type

Use story-map for release outcomes.

## Layout and meaning

Cards are grouped by explicit column, with text states and count/limit headers. No arrows.
Meaning comes from labels, shape, relationships and source IDs, not decoration.
Compare the complete source values below the figure before hand-off.

## Complexity budget

At most 12 items, fourteen connections where applicable, two focal source-linked cards.
Split by business boundary rather than shrink labels. The paragraph gate still
refuses fewer than five items and one actor; never invent an actor to bypass it.

## JSON additions

The common contract in references/style.md applies. This complete illustrative
input shows every required field. Source order is retained unless a calendar or
parent relation determines position. Omitted observations must be resolved, not
silently replaced with policy. Unknown fields are rejected.

```json
{
  "type": "kanban",
  "title": "Refund example \u00b7 kanban",
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
      "column": "Queue",
      "state": "queued",
      "owner": "Reviewer"
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "column": "Review",
      "state": "doing",
      "owner": "Reviewer"
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "column": "Done",
      "state": "done",
      "owner": "Reviewer"
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "column": "Queue",
      "state": "blocked",
      "owner": "Reviewer"
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "column": "Review",
      "state": "waiting",
      "owner": "Reviewer"
    }
  ],
  "edges": [],
  "columns": [
    "Queue",
    "Review",
    "Done"
  ],
  "limits": {
    "Review": 1
  }
}
```

## Output

Use assets/kanban.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.
