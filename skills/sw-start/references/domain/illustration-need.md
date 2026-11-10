# When an illustration is needed

Compare saved evidence with any existing picture. Do not use source hashes, and do not draw because a lifecycle stage
says drawing comes next. A direct request still uses this test.

## Fresh feature

No linked diagram, SVG, HTML or Mermaid companion exists for the feature.

Draw only when the picture clarifies at least two of these distinctions:

- two or more actors
- a branch, exception or decision
- a state change
- a dependency or hand-off
- data moving between owners

If fewer than five items and one actor carry the distinction, use a paragraph. Do not invent an actor, state or quantity
to pass that gate.

## Existing illustration

Compare the current story and its linked cards with the picture's visible labels, nodes, edges, source IDs, actors,
branches, quantities and boundaries.

Update the picture when any depicted fact changed, or when `scripts/check_borders.py` or `scripts/check_offline.py`
reports a finding. Leave it unchanged when only undeclared wording, approval status or an unrelated section changed.

## Current illustration

When every depicted fact still matches and both checks pass, write nothing. Return the existing paths, the compared
source IDs and the reason the picture is current.

## Ownership

Return paths and link text. The calling `sw-spec` run writes those links, recomputes the story hash and refreshes the
card. This skill does not edit the draft, rules, IDs or approval. After a new or updated illustration, `sw-spec` reruns
the graph and lint before review. A no-op still leaves that story gate to `sw-spec`.
