# Offline drawing contract

## Runtime and files

Resolve all paths from the loaded skill directory, never the session working
directory. Run the absolute scripts/render_diagram.py with absolute input JSON
and approved output paths. Exit 0 written, 2 invalid input/I/O, 3 use a paragraph.
Outputs can be .html or standalone .svg, with .mmd only for the nine direct
Mermaid grammars in type-picker.md. No external renderer is invoked.
Files are individually atomically replaced, not a multi-file transaction.
An old .mmd is not deleted when a basename is reused for another type.

## Common JSON

A UTF-8 object supplies type, title (96 characters), actors (one to six unique
names of 24 characters), nodes and optional edges. Each node has a local id (letter then letters/digits/underscore, at
most 24), label (32 characters), spec_ids (zero to three valid qualified or local kit references, 36 combined
visible characters) and optionally focal: true. At most two nodes are focal: emphasis is an
explicit editorial choice, never inferred from which node has IDs. Edge from/to name nodes; label is explicit, at most 48.
Labels are data, never markup. No CSS, SVG coordinates, HTML or URLs come from
JSON. Numeric observations must be finite. New types reject unknown fields;
per-type references own the additions. Do not fabricate actors to bypass the
paragraph gate (fewer than five items and one actor). Keep source IDs literal.
Optional motion is auto (default), none, reveal or loop; see references/motion.md.

The original eight types retain their documented contracts. Template types
are edited from shipped assets and checked, not accepted by the JSON renderer.

## Look: trace sheet

A flat white sheet with hairline edges on a cool grey ground; no shadows. Source IDs are the
signature: each card carries a mono tab on its top edge, and quantitative marks carry the same
chip beside their direct label. Indigo marks the one or two focal nodes; red is reserved for
failure, rejection and over-limit states, so it never doubles as emphasis. Status marks are
shape-coded (.mk-ok circle, .mk-fail triangle, .mk-stop square, .mk-run diamond) and always
paired with a word. Dark theme is designed, not inverted.

## Theme owner

assets/theme.css owns the skin. Each self-contained shell and SVG embeds those bytes; checks
reject stale shells. Neutral roles: --sw-bg, --sw-surface, --sw-tint, --sw-ink, --sw-muted,
--sw-hair, --sw-edge, --sw-rule. Meaning roles: --sw-focal, --sw-link, --sw-fail, --sw-ok,
--sw-warn with tints. Data colour: --series-1 to --series-5 (colour-blind-safe categorical,
used only when series are distinct; one series uses one colour), --ramp-1 to --ramp-5 (one
ordered hue for magnitude, with matching --ramp-tx-N text), and up/down/total classes for
signed change. Both themes follow prefers-color-scheme and honour data-theme on the root.
Use system sans for names and mono only for IDs and field names. No external fonts or images.

## Geometry and accessibility

One SVG per document has a title and description linked by aria-labelledby. Standalone SVG
has its namespace, inline stylesheet, one hairline sheet, a title row and every source ID;
it never depends on HTML CSS. Marks are labelled directly with name, value and ID chip, so no
numbered key is needed. The exact values and the connection list live once, in the data table
under the picture, which also links back to each node.

Connectors are orthogonal with rounded corners, one port each, and masked labels placed where
they overlap no card or foreign line. Flow diagrams read top to bottom because every connector
carries a label; lanes become columns. Radial, set and quantitative grammars use their own
geometry, not arbitrary box-to-box arrows. Split crowded pictures rather than shrinking type.
Automated checks do not prove semantic fidelity or full WCAG conformance.

## Safety and review

Run absolute scripts/check_borders.py and scripts/check_offline.py paths on every
artifact. Both accept directories. Border findings are L-024; offline findings
reject active content and remote resources. The SVG namespace is metadata, not a
network request. The checker is a conservative lint, not a general sanitizer.
Inspect light/dark, narrow viewports, print and reduced motion; compare every
branch, quantity, date, cardinality and source ID with saved evidence.
