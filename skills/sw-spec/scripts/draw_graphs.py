"""Cards and connector diagrams: flow graphs, trees, UML classes and database schemas."""

from __future__ import annotations

from draw_common import esc
from draw_flow import FEdge, FNode, draw, layout
from draw_layout import Canvas, ceil4, glyph, measure, num, tab_width, wrap
from draw_schema import tree_parents

FLOW_KINDS = (
    "architecture",
    "data-flow",
    "it-current-state",
    "deployment",
    "dp-integration",
    "process",
    "dependency",
)
LANE_KEY = {
    "architecture": "zone",
    "data-flow": "lane",
    "it-current-state": "department",
    "deployment": "zone",
    "dp-integration": "zone",
}


def card_dims(node, rows=(), min_w=188, label=None, mono_rows=False):
    label = node["label"] if label is None else label
    name_w = measure(label, 15, bold=True)
    row_w = max((measure(r, 12 if mono_rows else 13, mono=mono_rows) for r in rows), default=0)
    w = ceil4(max(min_w, 32 + max(name_w, row_w), tab_width(node) + 24))
    w = min(w, 336)
    name_lines = wrap(label, w - 32, 15, True)
    last = 26 + 22 * (len(name_lines) - 1) + (20 + 20 * (len(rows) - 1) if rows else 0)
    return w, ceil4(last + 16), name_lines


def draw_card(
    cv, node, x, y, w, h, rows=(), label=None, prefix="node", extra="", mono_rows=False, cls=None
):
    label = node["label"] if label is None else label
    lines = wrap(label, w - 32, 15, True)
    cls = cls or ("box focal" if node.get("focal") is True else "box")
    out = [
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="6" class="{cls}"/>'
    ]
    ty = y + 26
    for line in lines:
        out.append(f'<text x="{num(x + 16)}" y="{num(ty)}" class="node-name">{esc(line)}</text>')
        ty += 22
    ty -= 2
    for row in rows:
        out.append(
            f'<text x="{num(x + 16)}" y="{num(ty)}" class="{"ids" if mono_rows else "small"}">'
            f"{esc(row)}</text>"
        )
        ty += 20
    out.append(cv.tab(node, x + w - 12, y))
    out.append(extra)
    cv.node(node, "".join(out), (x, y, w, h), prefix)
    cv.grow(x, y, x + w, y + h)


def _rows(spec, node, kind):
    if kind == "process":
        return [f"In: {node['input']}", f"Out: {node['output']}"]
    if kind == "data-flow":
        return [node["payload"]]
    if kind == "architecture":
        return [node["kind"]]
    if kind == "it-current-state":
        return [node["condition"]]
    if kind == "deployment":
        n = node.get("replicas", 1)
        return [node["host"], f"{n} replica{'' if n == 1 else 's'}"]
    if kind == "dp-integration":
        return [node["protocol"]]
    incoming = sum(e["to"] == node["id"] for e in spec.get("edges", []))
    return [node.get("version", "Version unspecified"), f"{incoming} incoming"]


def lane_names(spec, kind):
    if kind not in LANE_KEY:
        return None
    if kind == "architecture":
        return list(spec["zones"])
    return list(dict.fromkeys(n[LANE_KEY[kind]] for n in spec["nodes"]))


def flow_nodes(spec, rows_of, lanes=None, key=None, label_of=None, prefix="node"):
    dims = {}
    for n in spec["nodes"]:
        label = label_of(n) if label_of else n["label"]
        dims[n["id"]] = card_dims(n, rows_of(n), label=label)
    width = max(d[0] for d in dims.values())
    out = []
    for n in spec["nodes"]:
        _, h, _ = dims[n["id"]]
        label = label_of(n) if label_of else None

        def render(cv, x, y, w, hh, n=n, label=label):
            draw_card(cv, n, x, y, w, hh, rows_of(n), label, prefix)

        out.append(
            FNode(
                n["id"],
                width,
                h,
                render,
                lanes.index(n[key]) if lanes and key else 0,
            )
        )
    return out


def flow_edges(spec, **extra):
    return [FEdge(e["from"], e["to"], e["label"], **extra) for e in spec.get("edges", [])]


def flow_graph(spec):
    kind = spec["type"]
    cv = Canvas()
    lanes = lane_names(spec, kind)
    nodes = flow_nodes(spec, lambda n: _rows(spec, n, kind), lanes, LANE_KEY.get(kind))
    edges = flow_edges(spec)
    plan = layout(nodes, edges, lanes)
    draw(cv, plan, nodes, edges)
    return cv


STATUS_MARK = {
    "added": ("circle", "mk-ok"),
    "removed": ("triangle", "mk-fail"),
    "changed": ("diamond", "mk-run"),
    "unchanged": ("square", "mk-stop"),
}


def _glyph(status, x, y):
    shape, cls = STATUS_MARK[status]
    return glyph(shape, x, y, cls, 5)


def delta(spec):
    cv = Canvas()
    nodes_spec = spec["nodes"]

    def widest(n):
        labels = [n["label"]]
        if n["status"] == "changed":
            labels = [n["before_label"], n["after_label"]]
        return max(labels, key=lambda s: measure(s, 15, True))

    dims = {n["id"]: card_dims(n, ["CHANGED"], label=widest(n), min_w=204) for n in nodes_spec}
    width = max(d[0] for d in dims.values()) + 20
    union = [FNode(n["id"], width, dims[n["id"]][1], None, 0) for n in nodes_spec]
    edges = flow_edges(spec)
    plan = layout(union, edges)
    panel_w = plan.right - plan.left + 48
    panel_h = plan.bottom - plan.top + 56
    changes = spec["changes"]
    for side, hidden, title in ((0, "added", "BEFORE"), (1, "removed", "AFTER")):
        ox = side * (panel_w + 32)
        cv.rect(ox, 0, panel_w, panel_h, "frame", 8, "under")
        cv.text(ox + 20, 28, title, "micro", layer="under", size=12)
        side_nodes = []
        visible = set()
        for n in nodes_spec:
            if n["status"] == hidden:
                continue
            visible.add(n["id"])
            label = n["label"]
            if n["status"] == "changed":
                label = n["before_label" if side == 0 else "after_label"]
            prefix = "after-node" if side == 1 and n["status"] != "added" else "node"

            def render(cv_, x, y, w, h, n=n, label=label, prefix=prefix):
                glyph = _glyph(n["status"], x + 22, y + h - 16)
                text_ = (
                    f'<text x="{num(x + 36)}" y="{num(y + h - 11)}" class="small">'
                    f"{n['status'].upper()}</text>"
                )
                draw_card(cv_, n, x, y, w, h, [], label, prefix, glyph + text_)

            side_nodes.append(FNode(n["id"], width, dims[n["id"]][1], render, 0))
        by_id = {n.id: n for n in side_nodes}
        ordered = [by_id[n["id"]] for n in nodes_spec if n["id"] in visible]

        def show(i, e, side=side, visible=visible):
            snap = spec["edges"][i].get("snapshot", "both")
            return (
                e.src in visible
                and e.dst in visible
                and snap in {"both", "before" if side == 0 else "after"}
            )

        draw(
            cv,
            plan,
            ordered,
            edges,
            dx=ox + 24,
            dy=44 - plan.top,
            visible=visible,
            edge_visible=show,
            ghosts=False,
        )
        for n in nodes_spec:
            if n["id"] not in visible:
                x, y, w, h = plan.place[n["id"]]
                cv.rect(x + ox + 24, y + 44 - plan.top, w, h, "ghost", 6, "under")
                cv.text(
                    x + ox + 24 + w / 2,
                    y + 44 - plan.top + h / 2 + 4,
                    "not in this snapshot",
                    "small",
                    "middle",
                    13,
                    layer="under",
                )
    base = panel_h + 28
    cv.text(0, base, "Changes", "micro", layer="over", size=12)
    for i, row in enumerate(changes):
        cv.text(0, base + 26 + i * 22, f"{i + 1}. {row}", "small", size=13, layer="over")
    return cv


def _tidy(spec, nodes_by_id):
    parent = tree_parents(spec)
    children = {n["id"]: [] for n in spec["nodes"]}
    for n in spec["nodes"]:
        if n["id"] in parent:
            children[parent[n["id"]]].append(n["id"])
    root = next(n["id"] for n in spec["nodes"] if n["id"] not in parent)
    pitch = max(d.w for d in nodes_by_id.values()) + 56
    pos, cursor = {}, [0.0]

    def place(i):
        kids = children[i]
        if not kids:
            pos[i] = cursor[0] + pitch / 2
            cursor[0] += pitch
        else:
            for k in kids:
                place(k)
            pos[i] = (pos[kids[0]] + pos[kids[-1]]) / 2

    place(root)
    return pos


def tree_graph(spec):
    kind = spec["type"]
    cv = Canvas()
    rows_of = (lambda n: [n["role"]]) if kind == "org-chart" else (lambda n: [])
    nodes = flow_nodes(spec, rows_of)
    by = {n.id: n for n in nodes}
    edges = flow_edges(spec)
    plan = layout(nodes, edges, fixed_x=_tidy(spec, by))
    draw(cv, plan, nodes, edges)
    return cv


def cardinality(cv, point, sign, kind):
    """Crow's-foot notation at one end of a vertical stub; sign points away from the box."""
    x, y = point
    out = []

    def bar(d):
        out.append(f"M {num(x - 6)} {num(y + sign * d)} H {num(x + 6)}")

    def foot(d):
        out.append(f"M {num(x)} {num(y + sign * d)} L {num(x - 7)} {num(y)}")
        out.append(f"M {num(x)} {num(y + sign * d)} L {num(x + 7)} {num(y)}")

    if kind == "1":
        bar(10)
        bar(15)
    elif kind == "N":
        foot(14)
    elif kind == "1..*":
        foot(14)
        bar(19)
    else:  # 0..1
        bar(10)
        cv.circle(x, y + sign * 17, 4, "hollow", layer="edges")
    if out:
        cv.path(" ".join(out), "edge", "edges")
    cv.grow(x - 8, y - 20, x + 8, y + 20)


def card_glyphs(from_card, to_card):
    def deco(cv, pts, back):
        first, last = pts[0], pts[-1]
        src_at_start = not back
        a, b = (from_card, to_card) if src_at_start else (to_card, from_card)
        cardinality(cv, first, 1, a)
        cardinality(cv, last, -1, b)

    return deco


def compartments(node, groups):
    rows = [row for group in groups for row in group]
    name_w = measure(node["label"], 15, True)
    w = ceil4(max(220, 32 + max([name_w] + [measure(r, 12, mono=True) for r in rows])))
    w = max(w, tab_width(node) + 24)
    h = ceil4(40 + sum(max(1, len(g)) * 20 + 10 for g in groups) + 6)
    return w, h


def draw_compartment_card(cv, node, x, y, w, h, groups, prefix="node"):
    cls = "box focal" if node.get("focal") is True else "box"
    out = [
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" '
        f'rx="6" class="{cls}"/>',
        f'<text x="{num(x + 16)}" y="{num(y + 26)}" class="node-name">{esc(node["label"])}</text>',
    ]
    cy = y + 38
    for group in groups:
        out.append(
            f'<line x1="{num(x)}" y1="{num(cy)}" x2="{num(x + w)}" y2="{num(cy)}" class="rule"/>'
        )
        cy += 6
        for row in group or [""]:
            cy += 20
            if row:
                out.append(
                    f'<text x="{num(x + 16)}" y="{num(cy - 5)}" class="ids">{esc(row)}</text>'
                )
        cy += 4
    out.append(cv.tab(node, x + w - 12, y))
    cv.node(node, "".join(out), (x, y, w, h), prefix)
    cv.grow(x, y, x + w, y + h)


UML_MARKS = {
    "association": dict(end="arrow"),
    "inheritance": dict(end="triangle"),
    "realization": dict(end="triangle", dashed=True),
    "composition": dict(start="diamond", end=None),
    "aggregation": dict(start="hollow-diamond", end=None),
    "dependency": dict(end="arrow", dashed=True),
}


def class_graph(spec):
    kind = spec["type"]
    cv = Canvas()
    groups = {
        n["id"]: (
            [n["attributes"], n["operations"]]
            if kind == "uml-class"
            else [n.get("fields", [])]
            if kind == "er"
            else [n["columns"]]
        )
        for n in spec["nodes"]
    }
    dims = {n["id"]: compartments(n, groups[n["id"]]) for n in spec["nodes"]}
    width = max(d[0] for d in dims.values())
    nodes = []
    for n in spec["nodes"]:

        def render(cv_, x, y, w, h, n=n):
            draw_compartment_card(cv_, n, x, y, w, h, groups[n["id"]])

        nodes.append(FNode(n["id"], width, dims[n["id"]][1], render))
    edges = []
    for e in spec.get("edges", []):
        if kind == "uml-class":
            edges.append(FEdge(e["from"], e["to"], e["label"], **UML_MARKS[e["kind"]]))
        else:
            edges.append(
                FEdge(
                    e["from"],
                    e["to"],
                    e["label"],
                    end=None,
                    deco=card_glyphs(e["from_card"], e["to_card"]),
                )
            )
    plan = layout(nodes, edges)
    draw(cv, plan, nodes, edges)
    return cv
