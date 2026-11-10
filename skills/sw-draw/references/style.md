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
names of 24 characters), nodes and optional edges. Each node has a local id
(letter then letters/digits/underscore, at most 24), label (32 characters), and
spec_ids (zero to three valid qualified or local kit references, 36 combined
visible characters). Edge from/to name nodes; label is explicit, at most 48.
Labels are data, never markup. No CSS, SVG coordinates, HTML or URLs come from
JSON. Numeric observations must be finite. New types reject unknown fields;
per-type references own the additions. Do not fabricate actors to bypass the
paragraph gate (fewer than five items and one actor). Keep source IDs literal.

The original eight types retain their documented contracts. New structured
types use motion none, reveal or loop; see references/motion.md. Template types
are edited from shipped assets and checked, not accepted by the JSON renderer.

## Look
Soft white cards with hairline edges and a gentle shadow on a grouped grey ground, rounded 12/18px corners, muted connectors, one crimson focal tint, blue for focus and links, and shape-coded status marks (.mk-ok circle, .mk-fail triangle, .mk-stop square, .mk-run diamond). Dark theme is derived, not inverted.

## Theme owner
assets/theme.css owns the new shell skin. Each self-contained shell and SVG
embeds those bytes; checks reject stale shells. Nine existing roles are retained:
--sw-bg, --sw-surface, --sw-tint, --sw-ink, --sw-muted, --sw-hair, --sw-accent,
--sw-accent-tint, --sw-link. Chart-only --series-1 through --series-5 distinguish
series with numeric keys and an exact data table. --sw-motion-fast and
--sw-motion-total bound optional motion. Both themes follow prefers-color-scheme.
Use system sans for names, mono only for IDs. No external fonts or images.

## Geometry and accessibility
One SVG per document has a title and description linked by aria-labelledby.
Standalone SVG has its namespace, inline stylesheet, paper background and all
source chips; it never depends on HTML CSS. ViewBox changes never resize markers.
Plot marks have a numbered evidence key so labels are not shrunk into tiny cells.
Exact source values and connection/change ledgers expose aggregation and meaning.
Use the data table and caption to interpret values; colour is supplementary.

Use full borders, outlines, tints and SVG lines. Keep at most two focal source-linked
cards; never invent an ID for emphasis. Standard diagram connectors use outside
tracks with distinct ports, readable ledgers and arrow markers. Radial, set and
quantitative grammars use their own geometry, not arbitrary box-to-box arrows.
Split crowded pictures rather than shrinking type. Automated checks do not prove
semantic fidelity, crossing-free routing or full WCAG conformance.

## Safety and review
Run absolute scripts/check_borders.py and scripts/check_offline.py paths on every
artifact. Both accept directories. Border findings are L-024; offline findings
reject active content and remote resources. The SVG namespace is metadata, not a
network request. The checker is a conservative lint, not a general sanitizer.
Inspect light/dark, narrow viewports, print and reduced motion; compare every
branch, quantity, date, cardinality and source ID with saved evidence.
