# Choose a question before a notation

First ask whether fewer than five steps and one actor fit in a paragraph. If so,
refuse diagram output and write that paragraph. Identify the reader and ambiguity.

| Reader's question | Type | Companion |
| --- | --- | --- |
| Who owns each step and where does work change hands? | swimlane | HTML only |
| Which decision leads down which path? | flowchart | Mermaid flowchart |
| What does one persona do and feel at each touchpoint? | journey | Mermaid journey |
| Which internal work supports visible customer stages? | service-blueprint | HTML only |
| What thin end-to-end outcome belongs in each release? | story-map | HTML only |
| Which events move one object between statuses? | state | Mermaid stateDiagram-v2 |
| In what order do participants exchange messages? | sequence | Mermaid sequenceDiagram |
| Which business entities relate, with what multiplicity? | er | Mermaid erDiagram |

If a request combines ownership and lifecycle, offer a swimlane for handoffs and a
separate state diagram for legal transitions. Do not mix their shapes. If feelings
are unknown, ask for evidence or offer flowchart; do not fabricate a journey curve.

Refuse architecture and infrastructure diagrams: these notations do not encode
deployment boundaries. Refuse metrics charts: counts and axes need a charting
workflow outside this skill. Refuse UI mockups: controls need a UI design workflow.
sw-spec can record the outstanding need, not render these unsupported formats.
