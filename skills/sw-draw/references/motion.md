# Bounded motion, static meaning

The new JSON types accept motion: none (default), reveal, or loop. No JavaScript.
Reveal gives the entire drawing one short 6px entrance; it never hides a semantic
item or implies sequencing that the source did not provide. Loop is a single
four-second dashed connector-flow cue, not indefinite autoplay. Its name denotes
flow around the path, not a repeating semantic state machine.

All labels, values, nodes and outcomes remain present in the initial and final
frame. Motion never changes geometry, order, evidence, source IDs or approval.
Reduced-motion and print disable animation and transforms completely. A standalone
SVG includes the same CSS, theme tokens, background and semantics.
For repeated or interactive playback, stop: that capability is not shipped.
