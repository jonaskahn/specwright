# Bounded motion, static meaning

`motion` defaults to `auto`: a drawing moves only when order or flow is part of what it
says. `none`, `reveal` and `loop` remain explicit overrides. Playback is CSS only, with no
JavaScript, and every frame, including the first, shows every label, mark and value.

| Behaviour | Types | Why |
| --- | --- | --- |
| Flow token: one dot follows each connector in turn and takes the colour of the node it reaches; three cycles, then it rests | process, data-flow, flowchart, swimlane, state, journey | The order of hand-offs or transitions is the content. |
| Message stepping: each message arrow is emphasised once, in order | sequence | Time order is the axis. |
| Staggered entrance: marks fade in source order (about 600 ms), or pop in place for dated marks | gantt, timeline | Reading order and baseline are reinforced; geometry never changes. |
| Static | every other type | They show snapshots or structure, and motion would imply a sequence the source does not state. |

Explicit `reveal` gives the whole drawing one short 6 px entrance. Explicit `loop` runs the
flow token on any drawing that has connectors.

The first frame is the final geometry: entrances change only opacity or a mark's own scale
around its centre, so a renderer that stops at frame zero still shows exact values. The
flow token is the single decorative mark hidden at rest. Reduced motion and print disable
every animation and transform; a standalone SVG carries the same CSS, theme tokens,
background and semantics.
