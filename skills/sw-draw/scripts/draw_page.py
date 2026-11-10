"""Assemble themed HTML and independently usable SVG without a browser."""

from __future__ import annotations

import re

from draw_common import ASSETS, card, esc, quote_mermaid, text
from draw_engine import render_geometry
from draw_types import GRAPHS, MERMAID

MARKERS = """<defs>
<marker id="arrow" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="8" markerHeight="8"
 orient="auto-start-reverse">
<path d="M 0 0 L 11 6 L 0 12 Z" class="solid"/>
</marker>
<marker id="triangle" viewBox="0 0 12 12" refX="11" refY="6" markerWidth="10" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 0 L 11 6 L 0 12 Z" class="box"/>
</marker>
<marker id="diamond" viewBox="0 0 16 12" refX="15" refY="6" markerWidth="12" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 6 L 8 0 L 15 6 L 8 12 Z" class="solid"/>
</marker>
<marker id="hollow-diamond" viewBox="0 0 16 12" refX="15" refY="6"
 markerWidth="12" markerHeight="10"
 orient="auto-start-reverse">
<path d="M 0 6 L 8 0 L 15 6 L 8 12 Z" class="box"/>
</marker>
</defs>"""


def evidence(spec):
    rows = []
    for i, n in enumerate(spec["nodes"]):
        parts = []
        for k, v in n.items():
            if k in {"id", "label", "spec_ids", "actor"}:
                continue
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            parts.append(f"{k}: {v}")
        rows.append((f"{i + 1}. {n['label']}", parts))
    return rows


def mermaid(spec):
    kind = spec["type"]
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


def render(spec):
    kind = spec["type"]
    width, height, body = render_geometry(spec)
    # Plot marks never replace the accessible evidence key or source-ID cards.
    if kind not in GRAPHS and kind not in {"uml-class", "db-schema", "tree", "org-chart", "kanban"}:
        for i, n in enumerate(spec["nodes"]):
            body += card(
                n,
                (1160, 100 + i * 190, 400, 160),
                [f"Item {i + 1} · see data table"],
                i < 2 and bool(n.get("spec_ids")),
            )
    ledger = []
    if kind == "architecture-delta":
        ledger += ["Change: " + v for v in spec["changes"]]
    for i, e in enumerate(spec.get("edges", [])):
        if kind == "uml-class":
            relation = f" [{e['kind']}]"
        elif kind == "db-schema":
            relation = f" [{e['from_card']} → {e['to_card']}]"
        else:
            relation = ""
        ledger.append(
            f"{i + 1}. {e['from']} → {e['to']}{relation}: {e['label']}"
            + (f" ({e['weight']:g} {spec['unit']})" if kind == "sankey" else "")
        )
    for name, parts in evidence(spec):
        ledger.append(name)
        # Each admitted field is short; wrap joined arrays without dropping text.
        for part in parts:
            while len(part) > 100:
                ledger.append("  " + part[:100])
                part = part[100:]
            ledger.append("  " + part)
    # Put the full connection ledger in SVG as well as HTML for standalone export.
    if ledger:
        body += text(60, height + 30, "Connections, changes and exact data", "node-name")
        for i, row in enumerate(ledger):
            body += text(60, height + 66 + i * 30, row, "small")
        height += 120 + len(ledger) * 30
        width = max(width, 1640)
    shell = (ASSETS / f"{kind}.html").read_text(encoding="utf-8")
    desc = re.search(r"<!--description-->(.*?)<!--/description-->", shell, re.S).group(1)
    style = re.search(r"<style>(.*?)</style>", shell, re.S).group(1)
    motion = spec.get("motion", "none")
    body = f'<g class="drawing motion-{motion}">{body}</g>'
    # SVG namespace is required by the format; it is not a fetched resource.
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" '
        f'width="{width:g}" role="img" aria-labelledby="diagram-title diagram-desc">'
        f'<title id="diagram-title">{esc(spec["title"])}</title>'
        f'<desc id="diagram-desc">{desc}</desc>'
        f"<style>{style}</style>{MARKERS}"
        f'<rect width="100%" height="100%" rx="18" class="paper"/>{body}</svg>'
    )
    links = "".join(
        f'<li><a href="#node-{n["id"]}">{esc(n["label"])}: '
        f"{esc(', '.join(n.get('spec_ids', [])) or 'no spec IDs')}</a></li>"
        for n in spec["nodes"]
    )
    table = (
        "<table><caption>Exact source values; numbers on marks refer to these rows.</caption>"
        "<tr><th>Item</th><th>Data</th></tr>"
    )
    for name, parts in evidence(spec):
        table += (
            f"<tr><th>{esc(name)}</th><td>{esc('; '.join(parts) or 'No extra fields')}</td></tr>"
        )
    table += "</table>"
    for key, value in [
        ("title", esc(spec["title"])),
        ("body", svg),
        ("links", links),
        ("data", table),
    ]:
        shell = re.sub(
            rf"<!--{key}-->.*?<!--/{key}-->",
            lambda _, k=key, v=value: f"<!--{k}-->{v}<!--/{k}-->",
            shell,
            flags=re.S,
        )
    return shell, mermaid(spec)


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
    """Frame an exported SVG like the cockpit: grouped ground, raised card, title row."""
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
    inner = svg[len(head): svg.rindex("</svg>")]
    style_end = inner.index("</style>") + len("</style>")
    prelude, rest = inner[:style_end], inner[style_end:]
    card = (
        '<rect width="100%" height="100%" fill="var(--sw-bg)"/>'
        f'<rect x="{pad}" y="{pad}" width="{w:g}" height="{h + bar:g}" rx="18" '
        'class="paper" style="filter:drop-shadow(0 6px 18px rgba(20,24,30,.18))"/>'
        f'<text x="{pad + 28}" y="{pad + 46}" class="node-name" '
        f'style="font-size:22px">{title}</text>'
        f'<line x1="{pad}" y1="{pad + bar - 8}" x2="{pad + w:g}" y2="{pad + bar - 8}" '
        'class="rule"/>'
    )
    return f'{new_head}{prelude}{card}<g transform="translate({pad} {pad + bar})">{rest}</g></svg>'
