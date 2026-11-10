# Offline drawing contract

## Common JSON
A UTF-8 object has type, title (96 characters), actors (one to six unique names),
nodes, and edges (defaults to empty). Each node has a short local id (letters
first, then letters/digits/underscore), label (32 characters), and spec_ids (zero
to three valid kit references; 36 displayed characters combined). Use empty IDs
only where no rule or AC applies. Qualified references are allowed.
An edge has from, to, and a nonempty label (48 characters).

Supply actual actor names even when not displayed. The paragraph gate uses node
count and actor count, not arrow count. Actor names allow 24 characters. Arrays
retain narrative order. The first state is initial; the last is the displayed
terminal state. Split if several terminal outcomes would make this misleading.
Per-type references add fields. No coordinates, CSS, HTML or URLs come from JSON.
Labels with <, controls, network references or active content are rejected; other
punctuation is escaped. Reference a BR rather than shorten a guard's meaning.

Run python3 scripts/render_diagram.py input.json output.html from the skill folder
or use absolute paths. Exit 0 means written; 2 means invalid input or I/O failure;
3 means write a paragraph, with no new output. Both checkers return 0 clean,
1 findings, 2 usage or I/O error. Findings go to stdout, errors to stderr.
Every script has --help. Files are individually replaced atomically, not as a
multi-file transaction. Do not reuse a basename for another type: an older Mermaid
companion is not deleted when switching to HTML-only output.

## Templates and geometry
Each asset opens as a complete worked refund example. Replaceable regions use
paired HTML comment markers title, body and links. Rendering replaces those and
the viewBox, leaving inline CSS and legend intact. Only shipped shells are used.
Outputs have an accessible SVG title and description, visible ID chips with
data-spec and data-spec-ids, local node anchors, and a Spec links list.
Grid/lane layout favours space over compactness. Outside gutters keep connections
away from boxes where possible. Crossing-free routing is not promised: inspect
arrows and labels, and split crowded branches. Keep one SVG per document.
System sans and monospace only; no external fonts, scripts, stylesheets or images.

## Colour and lines
Nine role tokens are set in :root and overridden in prefers-color-scheme:dark:
--sw-bg, --sw-surface, --sw-tint, --sw-ink, --sw-muted, --sw-hair, --sw-accent,
--sw-accent-tint and --sw-link. Text targets 4.5:1 against its actual background;
meaningful marks target 3:1. At most the first two spec-linked nodes use accent (one cell for blueprints);
shapes and IDs carry meaning without colour. No decorative texture is used.
Connector labels use paint-order:stroke and an opaque background-colour halo.
Use full borders, outlines, tints or SVG lines. L-024 wraps shared CSS shorthand
checks, not a full CSS parser; avoid all one-sided longhands too.
Offline checks deliberately reject even local images and font-face declarations.
The checker is a conservative lint, not an HTML sanitizer. Do not trust arbitrary
shells merely because they pass it.
