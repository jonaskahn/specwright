"""Assemble themed HTML and independently usable SVG without a browser."""

from __future__ import annotations

import re

import draw_notes
from draw_common import ASSETS, esc, quote_mermaid
from draw_engine import build
from draw_layout import measure, num
from draw_types import LEGACY, MERMAID

MARKERS = """<defs>
<marker id="arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="8" markerHeight="8"
 orient="auto-start-reverse">
<path d="M 0 0 L 11 6 L 0 12 Z" class="solid"/>
</marker>
<marker id="open" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="8" markerHeight="8"
 orient="auto-start-reverse">
<path d="M 0 1 L 10 6 L 0 11" class="open"/>
</marker>
<marker id="triangle" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 0 L 11 6 L 0 12 Z" class="hollow"/>
</marker>
<marker id="diamond" viewBox="0 0 16 12" refX="15" refY="6" markerWidth="12" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 6 L 8 0 L 15 6 L 8 12 Z" class="solid"/>
</marker>
<marker id="hollow-diamond" viewBox="0 0 16 12" refX="15" refY="6"
 markerWidth="12" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 6 L 8 0 L 15 6 L 8 12 Z" class="hollow"/>
</marker>
</defs>"""

# Motion is on by default only where order or flow is part of the meaning.
AUTO_MOTION = {
    "process": "loop",
    "data-flow": "loop",
    "dp-integration": "loop",
    "flowchart": "loop",
    "swimlane": "loop",
    "state": "loop",
    "loop": "loop",
    "journey": "loop",
    "sequence": "steps",
    "bar": "grow",
    "waterfall": "grow",
    "gantt": "grow",
    "timeline": "pop",
    "sankey": "grow",
    "line": "pop",
}
FLOW_SPEED = 180.0

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta content="width=device-width, initial-scale=1" name="viewport">
<meta content="light dark" name="color-scheme">
<title>{title}</title>
<style>{theme}
{page_css}
</style>
</head>
<body>
<main>
<p class="eyebrow">{eyebrow}</p>
<h1>{title}</h1>
<p>{description}</p>
<figure aria-label="Scrollable diagram">{svg}</figure>
<h2>Spec links and exact data</h2>
{table}
</main>
</body>
</html>
"""


def resolve_motion(spec, canvas):
    mode = spec.get("motion", "auto")
    kind = spec["type"]
    if mode == "none":
        return "none"
    if mode == "reveal":
        return "reveal"
    if mode == "loop":
        return "loop" if canvas.flows else "reveal"
    if kind == "pyramid" and spec.get("variant") != "funnel":
        return "none"
    chosen = AUTO_MOTION.get(kind, "none")
    if chosen == "loop" and not canvas.flows:
        return "none"
    return chosen


def flow_css(canvas, order):
    """Finite, destination-coloured token that follows each connector in turn."""
    flows = canvas.flows
    durations = [length / FLOW_SPEED + 0.25 for _, length, _ in flows]
    total = sum(durations) + 1.0
    frames, t = [], 0.0
    for (d, _length, dest), dur in zip(flows, durations, strict=True):
        start, end = t / total * 100, (t + dur - 0.25) / total * 100
        index = order.index(dest) % 5 + 1 if dest in order else 1
        base = f"offset-path:path('{d}');fill:var(--series-{index});"
        if start > 0.03:
            frames.append(f"{start - 0.02:.2f}%{{{base}offset-distance:0%;opacity:0}}")
        frames.append(f"{start:.2f}%{{{base}offset-distance:0%;opacity:1}}")
        frames.append(f"{end:.2f}%{{{base}offset-distance:100%;opacity:1}}")
        frames.append(f"{end + 0.02:.2f}%{{{base}offset-distance:100%;opacity:0}}")
        t += dur
    frames.append("100%{opacity:0}")
    return (
        "@keyframes sw-flow{" + "".join(frames) + "}\n"
        "@supports (offset-path: path('M0 0 H1')){"
        "@media (prefers-reduced-motion: no-preference){"
        ".motion-loop .flow-token{offset-rotate:0deg;"
        f"animation:sw-flow {total:.2f}s linear 600ms 3;"
        "}}}"
    )


def evidence(spec):
    rows = []
    for n in spec["nodes"]:
        parts = []
        for k, v in n.items():
            if k in {"id", "label", "spec_ids", "actor", "focal"}:
                continue
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            elif isinstance(v, dict):
                v = ", ".join(f"{a}: {b}" for a, b in v.items())
            parts.append(f"{k}: {v}")
        rows.append((n, parts))
    return rows


def connections(spec):
    names = {n["id"]: n["label"] for n in spec["nodes"]}
    kind = spec["type"]
    rows = []
    for e in spec.get("edges", []):
        extra = ""
        if kind == "uml-class":
            extra = f" [{e['kind']}]"
        elif kind in {"db-schema", "er"}:
            extra = f" [{e['from_card']} to {e['to_card']}]"
        elif kind == "sankey":
            extra = f" ({e['weight']:g} {spec['unit']})"
        rows.append(f"{names[e['from']]} → {names[e['to']]}{extra}: {e['label']}")
    return rows


def mermaid(spec):
    kind = spec["type"]
    if kind in LEGACY:
        import draw_legacy

        return draw_legacy.mermaid(spec)
    if kind not in MERMAID:
        return None
    q = quote_mermaid

    def title(n):
        return q(n["label"] + " " + " ".join(n.get("spec_ids", [])))

    nodes = spec["nodes"]
    if kind == "timeline":
        lines = ["timeline", "    title " + q(spec["title"])]
        lines += [f"    {n['date']} : {title(n)}" for n in nodes]
    elif kind == "gantt":
        lines = ["gantt", "    title " + q(spec["title"]), "    dateFormat YYYY-MM-DD"]
        lines += [f"    {title(n)} :{n['id']}, {n['start']}, {n['end']}" for n in nodes]
    elif kind == "quadrant":
        lines = [
            "quadrantChart",
            "    title " + q(spec["title"]),
            f"    x-axis Low {q(spec['x_axis'])} --> High",
            f"    y-axis Low {q(spec['y_axis'])} --> High",
        ]
        lines += [f"    {title(n)}: [{n['x']}, {n['y']}]" for n in nodes]
    elif kind == "tree":
        from draw_schema import tree_parents

        parents = tree_parents(spec)
        children = {n["id"]: [] for n in nodes}
        for n in nodes:
            if n["id"] in parents:
                children[parents[n["id"]]].append(n)
        root = next(n for n in nodes if n["id"] not in parents)
        lines = ["mindmap"]

        def visit(n, depth):
            lines.append("  " * depth + title(n))
            for child in children[n["id"]]:
                visit(child, depth + 1)

        visit(root, 1)
    else:
        return None
    return "\n".join(lines) + "\n"


def table(spec):
    out = [
        "<table><caption>Exact source values and spec links, in drawing order.</caption>"
        "<tr><th>Item</th><th>Spec IDs and data</th></tr>"
    ]
    for node, parts in evidence(spec):
        ids = ", ".join(node.get("spec_ids", [])) or "no spec IDs"
        detail = "; ".join([ids] + parts)
        out.append(
            f'<tr><th><a href="#node-{esc(node["id"])}">{esc(node["label"])}</a></th>'
            f"<td>{esc(detail)}</td></tr>"
        )
    out.append("</table>")
    links = connections(spec)
    if links:
        out.append(
            "<table><caption>Connections.</caption><tr><th>#</th><th>Relation</th></tr>"
            + "".join(
                f"<tr><th>{i + 1}</th><td>{esc(row)}</td></tr>" for i, row in enumerate(links)
            )
            + "</table>"
        )
    return "".join(out)


def render(spec, theme=None):
    kind = spec["type"]
    canvas = build(spec)
    width, height, body, (dx, dy) = canvas.finish(measure(spec["title"], 22, bold=True) + 64)
    motion = resolve_motion(spec, canvas)
    order = [n["id"] for n in spec["nodes"]]
    token = '<circle class="flow-token" cx="0" cy="0" r="5" aria-hidden="true"/>'
    dynamic = flow_css(canvas, order) if motion == "loop" and canvas.flows else ""
    theme = theme if theme is not None else (ASSETS / "theme.css").read_text(encoding="utf-8")
    desc = esc(draw_notes.DESCRIPTIONS[kind])
    style = theme + (("\n" + dynamic) if dynamic else "")
    svg = (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="{width}" role="img" aria-labelledby="diagram-title diagram-desc">'
        f'<title id="diagram-title">{esc(spec["title"])}</title>'
        f'<desc id="diagram-desc">{desc}</desc>'
        f"<style>{style}</style>{MARKERS}"
        f'<rect width="100%" height="100%" class="paper" data-bg="1"/>'
        f'<g transform="translate({dx} {dy})"><g class="drawing motion-{motion}">{body}'
        f"{token if motion == 'loop' and canvas.flows else ''}</g></g></svg>"
    )
    page = PAGE.format(
        title=esc(spec["title"]),
        theme=theme,
        page_css=f"svg {{ min-width: {num(min(width, 760))}px; }}",
        eyebrow=esc(draw_notes.name(kind)),
        description=desc,
        svg=svg,
        table=table(spec),
    )
    return page, mermaid(spec)


def standalone(page):
    """Extract only a renderer-owned SVG, including its stylesheet."""
    match = re.search(r"<svg\b.*?</svg>", page, re.S)
    if not match:
        raise ValueError("renderer did not produce SVG")
    svg = match.group(0)
    if "xmlns=" not in svg:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    if "<style>" not in svg:
        style = re.search(r"<style>.*?</style>", page, re.S).group(0)
        svg = svg.replace("</desc>", "</desc>" + style, 1)
    return _framed(svg) + "\n"


def _framed(svg):
    """Frame an exported SVG: a flat ground, one hairline sheet and a title row."""
    head = re.match(r"<svg\b[^>]*>", svg).group(0)
    box = re.search(r'viewBox="0 0 ([0-9.]+) ([0-9.]+)"', head)
    if not box or "data-framed" in head:
        return svg
    w, h = float(box.group(1)), float(box.group(2))
    pad, bar = 32, 72
    title = re.search(r'<title id="diagram-title">(.*?)</title>', svg, re.S).group(1)
    total_w, total_h = w + pad * 2, h + pad * 2 + bar
    new_head = head.replace(box.group(0), f'viewBox="0 0 {total_w:g} {total_h:g}"')
    new_head = re.sub(r'width="[0-9.]+"', f'width="{total_w:g}"', new_head, count=1)
    new_head = new_head.replace("<svg ", '<svg data-framed="1" ', 1)
    inner = svg[len(head) : svg.rindex("</svg>")]
    style_end = inner.index("</style>") + len("</style>")
    prelude, rest = inner[:style_end], inner[style_end:]
    rest = re.sub(r'<rect\b[^>]*width="100%"[^>]*\bclass="paper"[^>]*/>', "", rest, count=1)
    rest = re.sub(r'<rect\b[^>]*\bclass="paper"[^>]*width="100%"[^>]*/>', "", rest, count=1)
    card = (
        '<rect width="100%" height="100%" class="ground"/>'
        f'<rect x="{pad}" y="{pad}" width="{w:g}" height="{h + bar:g}" rx="8" class="sheet"/>'
        f'<text x="{pad + 28}" y="{pad + 46}" class="title-bar">{title}</text>'
        f'<line x1="{pad}" y1="{pad + bar - 8}" x2="{pad + w:g}" y2="{pad + bar - 8}" '
        'class="rule"/>'
    )
    return f'{new_head}{prelude}{card}<g transform="translate({pad} {pad + bar})">{rest}</g></svg>'
