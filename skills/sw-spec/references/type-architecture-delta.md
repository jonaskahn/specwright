# architecture-delta

## Best for

Structural change with a change ledger.

## Not this type

Use a table for attribute-only changes.

## Layout and meaning

Before and after share one layout. Each card states added, removed, changed or unchanged by glyph and word, and the change list names every edit.
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
  "type": "architecture-delta",
  "title": "Refund example \u00b7 architecture-delta",
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
      "status": "unchanged"
    },
    {
      "id": "n2",
      "label": "Policy",
      "spec_ids": [],
      "status": "added"
    },
    {
      "id": "n3",
      "label": "Decision",
      "spec_ids": [],
      "status": "changed",
      "before_label": "Manual decision",
      "after_label": "Evidence-backed decision"
    },
    {
      "id": "n4",
      "label": "Settlement",
      "spec_ids": [],
      "status": "removed"
    },
    {
      "id": "n5",
      "label": "Notice",
      "spec_ids": [],
      "status": "unchanged"
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
  ],
  "changes": [
    "Add policy review endpoint",
    "Retire legacy settlement handoff"
  ]
}
```

## Output

Use assets/architecture-delta.html as the shipped shell; run the loaded skill's absolute
scripts/render_diagram.py path with absolute JSON and approved .html or .svg paths.
No Mermaid grammar is claimed for this type; output is HTML or SVG only.

## Anti-patterns

Do not infer dates, amounts, ownership, cardinalities or approval from layout.
Retain branches, units and literal source IDs; never silently aggregate or omit
an observation. Review both themes, check the source-data table and run both
scripts/check_offline.py and scripts/check_borders.py before sharing.

Changed nodes require before_label and after_label. Edges accept snapshot before, after or both (default); panels
include only endpoints present in that snapshot. The union keeps stable node IDs. Added/removed components do not appear
in the other snapshot.
