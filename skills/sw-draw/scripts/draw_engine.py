"""Notation-specific geometry; semantic data never supplies executable SVG."""

from __future__ import annotations

import math
from datetime import date

from draw_common import card, circle, line, path, polygon, rect, text
from draw_schema import tree_parents
from draw_types import GRAPHS


def layout(spec):
    """Return non-overlapping reading cards; marks have separate geometry."""
    kind, nodes = spec["type"], spec["nodes"]
    if kind in GRAPHS or kind in {"uml-class", "db-schema"}:
        height = 440 if kind == "uml-class" else 240 if kind == "db-schema" else 160
        return {n["id"]: (80, 100 + i * (height + 80), 400, height) for i, n in enumerate(nodes)}
    if kind in {"tree", "org-chart"}:
        parent = tree_parents(spec)
        result = {}
        for i, n in enumerate(nodes):
            depth, cursor = 0, n["id"]
            while cursor in parent:
                depth += 1
                cursor = parent[cursor]
            result[n["id"]] = (80 + depth * 460, 100 + i * 200, 400, 140)
        return result
    if kind == "kanban":
        slots = dict.fromkeys(spec["columns"], 0)
        result = {}
        for n in nodes:
            col = spec["columns"].index(n["column"])
            result[n["id"]] = (60 + col * 440, 150 + slots[n["column"]] * 190, 400, 160)
            slots[n["column"]] += 1
        return result
    # Separate the complete evidence key from the plotting area: dense values
    # never force source IDs or long names into tiny marks.
    return {n["id"]: (1160, 100 + i * 190, 400, 160) for i, n in enumerate(nodes)}


def edge_routes(spec, boxes):
    out = []
    edges = spec.get("edges", [])
    for i, e in enumerate(edges):
        a, b = boxes[e["from"]], boxes[e["to"]]
        # Distinct ports and outside tracks keep connections out of other cards.
        source = [x for x in edges if x["from"] == e["from"]]
        target = [x for x in edges if x["to"] == e["to"]]
        sy = a[1] + 24 + (a[3] - 48) * (source.index(e) + 1) / (len(source) + 1)
        ey = b[1] + 24 + (b[3] - 48) * (target.index(e) + 1) / (len(target) + 1)
        gutter = max(box[0] + box[2] for box in boxes.values()) + 80 + i * 64
        sx, ex = a[0] + a[2], b[0] + b[2]
        if e["from"] == e["to"]:
            ey = sy + 24
        d = (
            (
                f"M {sx:g} {sy:g} H {gutter - 8:g} "
                f"Q {gutter:g} {sy:g} {gutter:g} {sy + 8:g} V {ey - 8:g} "
                f"Q {gutter:g} {ey:g} {gutter - 8:g} {ey:g} H {ex:g}"
            )
            if ey > sy + 16
            else f"M {sx:g} {sy:g} H {gutter:g} V {ey:g} H {ex:g}"
        )
        rel = e.get("kind", "association")
        marker = {
            "inheritance": "triangle",
            "realization": "triangle",
            "composition": "diamond",
            "aggregation": "hollow-diamond",
        }.get(rel, "arrow")
        dashed = rel in {"realization", "dependency"} or (
                spec["type"] == "architecture-delta" and "removed" in e["label"].lower()
        )
        attr = (
            f'marker-start="url(#{marker})"'
            if rel in {"composition", "aggregation"}
            else f'marker-end="url(#{marker})"'
        )
        out.append(path(d, "edge dashed" if dashed else "edge", attr))
        # The numbered connection ledger is exact even when a long route crosses
        # another; labels never float over unrelated nodes.
        out.append(text(gutter + 8, (sy + ey) / 2, str(i + 1), "halo"))
    return "".join(out)


def delta(spec):
    """Two synchronized snapshots; union nodes retain stable source identifiers."""
    nodes = spec["nodes"]
    height = 180 + len(nodes) * 200
    panel_width = 580 + 64 * len(spec.get("edges", []))
    out = []
    for side, excluded in ((0, "added"), (1, "removed")):
        offset = 40 + side * (panel_width + 40)
        out.extend(
            [
                rect(offset, 50, panel_width, height - 70, "frame"),
                text(offset + 20, 84, "BEFORE" if side == 0 else "AFTER", "node-name"),
            ]
        )
        visible = [n for n in nodes if n["status"] != excluded]
        boxes = {n["id"]: (offset + 20, 120 + nodes.index(n) * 200, 400, 140) for n in visible}
        edges = [
            e
            for e in spec.get("edges", [])
            if e["from"] in boxes
               and e["to"] in boxes
               and e.get("snapshot", "both") in {"both", "before" if side == 0 else "after"}
        ]
        panel = dict(spec, nodes=visible, edges=edges)
        out.append(edge_routes(panel, boxes))
        for n in visible:
            # One authoritative local anchor per node; both appearances still
            # retain literal source chips and explicit status text.
            display = dict(n)
            if n["status"] == "changed":
                display["label"] = n["before_label" if side == 0 else "after_label"]
            content = card(display, boxes[n["id"]], [n["status"].upper()])
            if side == 1 and n["status"] != "added":
                content = content.replace('id="node-', 'id="after-node-')
            out.append(content)
    return 120 + 2 * panel_width, height, "".join(out)


def zoned_graph(spec):
    """Show boundaries without treating connection direction as containment."""
    kind, nodes = spec["type"], spec["nodes"]
    key = {
        "architecture": "zone",
        "data-flow": "lane",
        "it-current-state": "department",
        "deployment": "zone",
        "dp-integration": "zone",
    }[kind]
    groups = list(dict.fromkeys(n[key] for n in nodes))
    width = 1060 + 64 * len(spec.get("edges", []))
    boxes = layout(spec)
    out = []
    for name in groups:
        indices = [i for i, n in enumerate(nodes) if n[key] == name]
        # Each group owns contiguous rows. Keep labels in the same evidence order
        # within their group and make placement deterministic across renders.
        start = sum(sum(n[key] == g for n in nodes) for g in groups[: groups.index(name)])
        y = 100 + start * 240
        out.extend(
            [
                rect(40, y - 40, width - 80, len(indices) * 240 - 20, "frame"),
                text(60, y - 12, name, "node-name"),
            ]
        )
        for j, i in enumerate(indices):
            boxes[nodes[i]["id"]] = (80, y + j * 240, 400, 160)
    out.append(edge_routes(spec, boxes))
    for i, n in enumerate(nodes):
        detail = {
            "architecture": [n.get("kind", ""), n.get("zone", "")],
            "data-flow": [n.get("lane", ""), n.get("payload", "")],
            "it-current-state": [n.get("department", ""), n.get("condition", "")],
            "deployment": [n.get("host", ""), f"{n.get('replicas', 1)} replicas"],
            "dp-integration": [n.get("zone", ""), n.get("protocol", "")],
        }[kind]
        out.append(card(n, boxes[n["id"]], detail, i < 2 and bool(n.get("spec_ids"))))
    return width, 180 + len(nodes) * 240, "".join(out)


def graph(spec):
    kind, nodes = spec["type"], spec["nodes"]
    if kind == "architecture-delta":
        return delta(spec)
    if kind in {"architecture", "data-flow", "it-current-state", "deployment", "dp-integration"}:
        return zoned_graph(spec)
    boxes = layout(spec)
    out = [edge_routes(spec, boxes)]
    for i, n in enumerate(nodes):
        detail = []
        if kind == "architecture":
            detail = [f"{n['kind']} · {n['zone']}"]
        elif kind == "architecture-delta":
            detail = [f"{n['status'].upper()} · before → after"]
        elif kind == "it-current-state":
            detail = [n["department"], n["condition"]]
        elif kind == "process":
            detail = [f"In: {n['input']}", f"Out: {n['output']}"]
        elif kind == "data-flow":
            detail = [n["lane"], n["payload"]]
        elif kind == "dp-integration":
            detail = [n["zone"], n["protocol"]]
        elif kind == "deployment":
            detail = [f"{n['host']} · {n['zone']}", f"{n['replicas']} replicas"]
        elif kind == "dependency":
            detail = [
                f"{sum(e['to'] == n['id'] for e in spec.get('edges', []))} incoming",
                n.get("version", "Version unspecified"),
            ]
        elif kind == "uml-class":
            detail = ["Attributes", *n["attributes"], "Operations", *n["operations"]]
        elif kind == "db-schema":
            detail = n["columns"]
        if kind == "uml-class":
            box = boxes[n["id"]]
            box = (box[0], box[1], box[2], max(box[3], 100 + 24 * len(detail)))
        else:
            box = boxes[n["id"]]
        out.append(card(n, box, detail, i < 2 and bool(n.get("spec_ids"))))
        if kind in {"uml-class", "db-schema"}:
            out.append(line(box[0], box[1] + 38, box[0] + box[2], box[1] + 38))
    width = max(b[0] + b[2] for b in boxes.values()) + max(
        600, len(spec.get("edges", [])) * 64 + 160
    )
    height = max(b[1] + b[3] for b in boxes.values()) + 100
    return width, height, "".join(out)


def hierarchy(spec):
    kind, nodes = spec["type"], spec["nodes"]
    if kind in {"tree", "org-chart"}:
        boxes = layout(spec)
        out = edge_routes(spec, boxes)
        for n in nodes:
            out += card(n, boxes[n["id"]], [n["role"]] if kind == "org-chart" else [])
        return (
            max(b[0] + b[2] for b in boxes.values()) + 1200,
            max(b[1] + b[3] for b in boxes.values()) + 80,
            out,
        )
    out = []
    if kind == "nested":
        children = {n["id"]: [] for n in nodes}
        for n in nodes:
            if n.get("parent"):
                children[n["parent"]].append(n)
        root = next(n for n in nodes if not n.get("parent"))

        def size(n):
            return 100 + sum(size(c) + 20 for c in children[n["id"]])

        def draw(n, x, y, w):
            h = size(n)
            out.extend([rect(x, y, w, h, "box", 8), text(x + 20, y + 30, n["label"])])
            cy = y + 64
            for child in children[n["id"]]:
                draw(child, x + 24, cy, w - 48)
                cy += size(child) + 20

        draw(root, 40, 60, 1040)
        height = size(root) + 120
    elif kind == "layer-stack":
        for i, n in enumerate(nodes):
            y = 80 + i * 140
            out.extend(
                [
                    rect(80, y, 920, 110, "box focal" if i == 0 else "box"),
                    text(104, y + 36, f"{i + 1}. {n['label']}"),
                    text(104, y + 72, n["responsibility"]),
                ]
            )
        height = 100 + len(nodes) * 140
    elif kind == "loop":
        positions = {
            n["id"]: (
                540 + 400 * math.cos(-math.pi / 2 + i * 2 * math.pi / len(nodes)),
                540 + 400 * math.sin(-math.pi / 2 + i * 2 * math.pi / len(nodes)),
            )
            for i, n in enumerate(nodes)
        }
        for e in spec["edges"]:
            a, b = positions[e["from"]], positions[e["to"]]
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            ax, ay = a[0] + 38 * dx / length, a[1] + 38 * dy / length
            bx, by = b[0] - 38 * dx / length, b[1] - 38 * dy / length
            out.append(path(f"M {ax:g} {ay:g} L {bx:g} {by:g}", "edge", 'marker-end="url(#arrow)"'))
        for i, n in enumerate(nodes):
            x, y = positions[n["id"]]
            out.extend(
                [
                    circle(x, y, 38, "box"),
                    text(x, y + 6, i + 1, anchor="middle"),
                    text(x, y + 64, n["label"], anchor="middle"),
                ]
            )
        height = 1080
    else:  # Fishbone: cause category branches converge on the named effect.
        height = max(760, 180 + len(nodes) * 100)
        mid = height / 2
        out.extend(
            [line(80, mid, 960, mid, "edge"), text(960, mid - 20, spec["effect"], "halo", "end")]
        )
        for i, n in enumerate(nodes):
            x = 160 + (i // 2) * 190
            y = mid + (-1 if i % 2 == 0 else 1) * (170 + 20 * (i // 4))
            out.extend(
                [
                    line(x, y, x + 100, mid, "edge"),
                    text(x - 50, y - 28, n["category"]),
                    text(x - 50, y - 4, n["label"]),
                ]
            )
    return 1640, max(height, 120 + len(nodes) * 190), "".join(out)


def axes(out, spec, x_label=None, y_label=None, scale=1, ticks=True):
    out.extend(
        [
            line(100, 680, 1040, 680),
            line(100, 100, 100, 680),
            text(570, 744, x_label or spec.get("x_axis", ""), "small", "middle"),
            text(100, 72, y_label or spec.get("y_axis", spec.get("unit", "")), "small"),
        ]
    )
    for value in (0, 0.25, 0.5, 0.75, 1) if ticks else ():
        out.extend(
            [
                text(84, 686 - value * 560, f"{value * scale:g}", "small", "end"),
                line(100, 680 - value * 560, 1040, 680 - value * 560),
            ]
        )


def charts(spec):
    kind, nodes = spec["type"], spec["nodes"]
    out = []
    if kind in {"quadrant", "scatter", "wardley"}:
        axes(
            out,
            spec,
            "Evolution: genesis → commodity" if kind == "wardley" else None,
            "Visibility: low → high" if kind == "wardley" else None,
        )
        if kind == "quadrant":
            out.extend([line(570, 100, 570, 680), line(100, 390, 1040, 390)])
        swarm = {}
        for i, n in enumerate(nodes):
            x = 100 + 940 * n["evolution" if kind == "wardley" else "x"]
            y = 680 - 560 * n["visibility" if kind == "wardley" else "y"]
            if spec.get("variant") == "box-plot":
                lo, q1, med, q3, hi = n["samples"]
                out.extend(
                    [
                        line(100 + 940 * lo, y, 100 + 940 * hi, y),
                        rect(100 + 940 * q1, y - 20, 940 * (q3 - q1), 40),
                        line(100 + 940 * med, y - 20, 100 + 940 * med, y + 20),
                    ]
                )
            else:
                r = math.sqrt(n.get("size", 36)) if spec.get("variant") == "bubble" else 8
                if spec.get("variant") == "beeswarm":
                    # Same quantized x bins, deterministic nearest-free vertical slots.
                    x = 100 + 940 * (round(n["x"] * 20) / 20)
                    used = swarm.setdefault(round(n["x"] * 20), 0)
                    offset = (used + 1) // 2 * (1 if used % 2 else -1)
                    y = 390 + offset * 24
                    swarm[round(n["x"] * 20)] = used + 1
                out.append(circle(x, y, r, "series-" + str(i % 5 + 1)))
            out.append(text(x + 12, y - 12, str(i + 1), "halo"))
        if kind == "wardley":
            by_id = {n["id"]: n for n in nodes}
            for e in spec.get("edges", []):
                a, b = by_id[e["from"]], by_id[e["to"]]
                out.append(
                    line(
                        100 + 940 * a["evolution"],
                        680 - 560 * a["visibility"],
                        100 + 940 * b["evolution"],
                        680 - 560 * b["visibility"],
                        "edge",
                    )
                )
    elif kind in {"radar", "polar"}:
        count = len(spec["axes"]) if kind == "radar" else len(nodes)
        for fraction in (0.25, 0.5, 0.75, 1):
            out.extend(
                [
                    circle(540, 400, 270 * fraction, "open"),
                    text(550, 400 - 270 * fraction, f"{fraction * spec['maximum']:g}", "small"),
                ]
            )
        labels = spec["axes"] if kind == "radar" else [n["label"] for n in nodes]
        for i, name in enumerate(labels):
            angle = -math.pi / 2 + i * 2 * math.pi / count
            x, y = 540 + 270 * math.cos(angle), 400 + 270 * math.sin(angle)
            out.extend(
                [
                    line(540, 400, x, y),
                    text(
                        540 + 320 * math.cos(angle),
                        400 + 320 * math.sin(angle),
                        name,
                        "small",
                        "middle",
                    ),
                ]
            )
        if kind == "radar":
            for i, n in enumerate(nodes):
                pts = [
                    (
                        540
                        + 270
                        * v
                        / spec["maximum"]
                        * math.cos(-math.pi / 2 + j * 2 * math.pi / count),
                        400
                        + 270
                        * v
                        / spec["maximum"]
                        * math.sin(-math.pi / 2 + j * 2 * math.pi / count),
                    )
                    for j, v in enumerate(n["values"])
                ]
                out.append(polygon(pts, "series-" + str(i % 5 + 1)))
        else:
            for i, n in enumerate(nodes):
                a = -math.pi / 2 + i * 2 * math.pi / count
                r = 270 * n["value"] / spec["maximum"]
                out.extend(
                    [
                        line(540, 400, 540 + r * math.cos(a), 400 + r * math.sin(a), "edge"),
                        circle(
                            540 + r * math.cos(a),
                            400 + r * math.sin(a),
                            8,
                            "series-" + str(i % 5 + 1),
                        ),
                    ]
                )
    elif kind in {"pyramid", "treemap", "heatmap"}:
        total = sum(n["value"] for n in nodes) or 1
        maximum = max(n["value"] for n in nodes) or 1
        left = 80
        for i, n in enumerate(nodes):
            if kind == "pyramid":
                # Ordinal tiers for a hierarchy; funnel width is proportional.
                width = (
                    960 * n["value"] / maximum
                    if spec.get("variant") == "funnel"
                    else 200 + i * 760 / max(1, len(nodes) - 1)
                )
                x, y, w, h = 560 - width / 2, 90 + i * 110, width, 100
                out.append(
                    polygon([(x, y), (x + w, y), (x + w + 30, y + h), (x - 30, y + h)], "box")
                )
            elif kind == "treemap":
                x, y, w, h = left, 120, 960 * n["value"] / total, 560
                if spec.get("variant") == "marimekko":
                    bottom = y + h
                    for j, v in enumerate(n["segments"]):
                        hh = h * v / sum(n["segments"])
                        out.append(rect(x, bottom - hh, w, hh, "series-" + str(j % 5 + 1), 0))
                        bottom -= hh
                else:
                    out.append(rect(x, y, w, h, "box", 0))
                left += w
            else:
                x = 140 + spec["columns"].index(n["column"]) * 170
                y = 100 + spec["rows"].index(n["row"]) * 120
                w, h = 160, 110
                out.extend(
                    [
                        rect(
                            x,
                            y,
                            w,
                            h,
                            "series-" + str(min(5, 1 + int(4 * n["value"] / maximum))),
                            0,
                        ),
                        text(x + 10, y + 30, n["label"], "small"),
                    ]
                )
            out.append(text(x + w / 2, y + h / 2, f"{i + 1}: {n['value']:g}", "halo", "middle"))
        if kind == "heatmap":
            for i, c in enumerate(spec["columns"]):
                out.append(text(140 + i * 170, 70, c))
            for i, r in enumerate(spec["rows"]):
                out.append(text(130, 160 + i * 120, r, "small", "end"))
        out.append(text(80, 60, spec["unit"]))
    elif kind == "bar":
        maximum = max([n["value"] for n in nodes] + [n.get("compare", 0) for n in nodes]) or 1
        for i, n in enumerate(nodes):
            y = 100 + i * 90
            x = 120 + 840 * n["value"] / maximum
            if spec.get("variant") == "dumbbell":
                xx = 120 + 840 * n["compare"] / maximum
                out.extend(
                    [
                        line(x, y + 20, xx, y + 20, "edge"),
                        circle(x, y + 20, 8, "solid"),
                        circle(xx, y + 20, 8, "series-1"),
                        text(xx, y + 52, f"Compare {n['compare']:g}"),
                    ]
                )
            else:
                out.append(
                    rect(120, y, 840 * n["value"] / maximum, 44, "series-" + str(i % 5 + 1), 0)
                )
            out.extend([text(100, y + 28, i + 1, "small", "end"), text(x + 12, y + 28, n["value"])])
        out.extend(
            [
                line(120, 80, 120, 100 + len(nodes) * 90),
                text(120, 60, f"Zero baseline · {spec['unit']}"),
            ]
        )
    elif kind == "waterfall":
        intervals = []
        running = 0
        for n in nodes:
            start = 0 if n.get("total") else running
            end = n["value"] if n.get("total") else start + n["value"]
            intervals.append((start, end))
            running = end
        lo = min(0, min(min(v) for v in intervals))
        hi = max(1, max(max(v) for v in intervals))

        def yy(v):
            return 680 - 560 * (v - lo) / (hi - lo)

        out.extend([line(80, yy(0), 1060, yy(0)), text(80, 60, spec["unit"])])
        for i, (a, b) in enumerate(intervals):
            x = 100 + i * 104
            out.extend(
                [
                    rect(
                        x,
                        min(yy(a), yy(b)),
                        80,
                        max(1, abs(yy(b) - yy(a))),
                        "series-" + str(i % 5 + 1),
                        0,
                    ),
                    text(x, yy(b) - 12, f"{i + 1}: {b:g}", "halo"),
                ]
            )
            if i < len(intervals) - 1:
                out.append(line(x + 80, yy(b), x + 104, yy(b)))
    else:  # line family: temporal/ordinal categories and explicit series.
        variant = spec.get("variant", "line")
        categories = spec["categories"]
        maximum = max(v for n in nodes for v in n["values"]) or 1
        if variant == "streamgraph":
            maximum = max(sum(n["values"][j] for n in nodes) for j in range(len(categories))) or 1
        axes(
            out,
            spec,
            "Ordered categories",
            spec["unit"],
            maximum,
            variant not in {"bump", "ridgeline", "streamgraph"},
        )
        if variant == "bump":
            for rank in range(len(nodes)):
                out.append(
                    text(
                        84,
                        146 + rank * 500 / max(1, len(nodes) - 1),
                        f"Rank {rank + 1}",
                        "small",
                        "end",
                    )
                )
        elif variant == "ridgeline":
            for i, _n in enumerate(nodes):
                out.extend(
                    [
                        line(100, 180 + i * 100, 1040, 180 + i * 100),
                        text(84, 186 + i * 100, str(i + 1), "small", "end"),
                    ]
                )
        elif variant == "streamgraph":
            out.append(text(100, 90, "Centered baseline; thickness = amount", "small"))
        previous = [0] * len(categories)
        for i, n in enumerate(nodes):
            pts = []
            for j, v in enumerate(n["values"]):
                x = 100 + 940 * j / (len(categories) - 1)
                y = 680 - 560 * v / maximum
                if variant == "slopegraph":
                    y = 680 - 560 * v / maximum
                if variant == "bump":
                    ordered = sorted(nodes, key=lambda nn: (-nn["values"][j], nn["id"]))
                    y = 140 + ordered.index(n) * 500 / max(1, len(nodes) - 1)
                if variant == "ridgeline":
                    y = 180 + i * 100 - 70 * v / maximum
                if variant == "streamgraph":
                    total = sum(nn["values"][j] for nn in nodes)
                    y = 390 + 280 * total / maximum - 560 * (previous[j] + v) / maximum
                pts.append((x, y))
            cls = "series-" + str(i % 5 + 1)
            if variant in {"ridgeline", "streamgraph"}:
                base = [
                    (
                        100 + 940 * j / (len(categories) - 1),
                        390
                        + 280 * sum(nn["values"][j] for nn in nodes) / maximum
                        - 560 * previous[j] / maximum
                        if variant == "streamgraph"
                        else 180 + i * 100,
                    )
                    for j in reversed(range(len(categories)))
                ]
                out.append(polygon(pts + base, cls))
                if variant == "streamgraph":
                    previous = [a + b for a, b in zip(previous, n["values"], strict=True)]
            else:
                d = "M " + " L ".join(f"{x:g} {y:g}" for x, y in pts)
                out.append(path(d, "edge " + cls))
                for x, y in pts:
                    out.append(circle(x, y, 5, cls))
        for j, c in enumerate(categories):
            out.append(text(100 + 940 * j / (len(categories) - 1), 716, c, "small", "middle"))
    return 1640, max(900, 160 + len(nodes) * 190), "".join(out)


def temporal(spec):
    kind, nodes = spec["type"], spec["nodes"]
    values = [
        date.fromisoformat(n["date" if kind == "timeline" else "start"]).toordinal() for n in nodes
    ]
    ends = (
        values if kind == "timeline" else [date.fromisoformat(n["end"]).toordinal() for n in nodes]
    )
    lo, hi = min(values), max(ends)

    def xx(d):
        return 100 + 900 * (d - lo) / max(1, hi - lo)

    out = [text(80, 50, "Calendar days; equal distances mean equal elapsed time")]
    if kind == "timeline":
        out.append(line(100, 400, 1000, 400, "edge"))
    for i, n in enumerate(nodes):
        x = xx(values[i])
        if kind == "timeline":
            y = 140 + i * 44 if i % 2 == 0 else 480 + i * 44
            out.extend(
                [
                    line(x, 400, x, y),
                    circle(x, 400, 7),
                    text(x + 8, y, n["date"] + " · " + str(i + 1), "halo"),
                ]
            )
        else:
            y = 120 + i * 90
            out.extend(
                [
                    rect(x, y, max(3, xx(ends[i]) - x), 46, "series-" + str(i % 5 + 1)),
                    text(x, y - 12, f"{i + 1}: {n['start']} → {n['end']}"),
                ]
            )
    return 1640, max(1000, 150 + len(nodes) * 190), "".join(out)


def other(spec):
    kind, nodes = spec["type"], spec["nodes"]
    if kind in {"timeline", "gantt"}:
        return temporal(spec)
    if kind in {"uml-class", "db-schema"}:
        return graph(spec)
    out = []
    if kind == "kanban":
        boxes = layout(spec)
        for i, c in enumerate(spec["columns"]):
            count = sum(n["column"] == c for n in nodes)
            limit = spec.get("limits", {}).get(c)
            title = f"{c} · {count}" + (
                f"/{limit}" + (" OVER LIMIT" if count > limit else "") if limit else ""
            )
            out.extend([rect(40 + i * 440, 60, 432, 60, "box"), text(60 + i * 440, 96, title)])
        for n in nodes:
            out.append(
                card(n, boxes[n["id"]], [n["state"].upper(), n["owner"]], n["state"] == "blocked")
            )
        return (
            80 + 440 * len(spec["columns"]),
            max(b[1] + b[3] for b in boxes.values()) + 80,
            "".join(out),
        )
    if kind == "venn":
        for i, n in enumerate(nodes):
            out.extend(
                [
                    circle(380 + i * 180, 350 + (i % 2) * 100, 240, "set"),
                    text(240 + i * 240, 100, n["label"]),
                ]
            )
        members = {v for n in nodes for v in n["members"]}
        for i, v in enumerate(sorted(members)):
            sets = [j + 1 for j, n in enumerate(nodes) if v in n["members"]]
            out.append(text(80, 760 + i * 32, f"{v}: sets " + ", ".join(str(j) for j in sets)))
        return 1640, max(1100, 820 + len(members) * 32, 160 + len(nodes) * 190), "".join(out)
    if kind == "dp-security-matrix":
        for j, c in enumerate(spec["columns"]):
            out.append(text(300 + j * 240, 80, c))
        for i, n in enumerate(nodes):
            y = 140 + i * 70
            out.append(text(40, y + 32, n["label"]))
            for j, v in enumerate(n["permissions"]):
                out.extend(
                    [
                        rect(280 + j * 240, y, 230, 54, "box"),
                        text(
                            300 + j * 240,
                            y + 34,
                            {"allow": "✓ ALLOW", "deny": "× DENY", "unknown": "? UNKNOWN"}[v],
                        ),
                    ]
                )
        return 1640, max(900, 160 + len(nodes) * 190), "".join(out)
    # Sankey uses one scale for every band, so widths retain quantitative meaning.
    by_id = {n["id"]: n for n in nodes}
    totals = {
        n["id"]: max(
            sum(e["weight"] for e in spec["edges"] if e["from"] == n["id"]),
            sum(e["weight"] for e in spec["edges"] if e["to"] == n["id"]),
        )
        for n in nodes
    }
    scale = 500 / max(1, sum(totals.values()))
    slots = {}
    cursors = dict.fromkeys(range(4), 100)
    for n in nodes:
        st = n["stage"]
        h = max(4, totals[n["id"]] * scale)
        slots[n["id"]] = (100 + st * 300, cursors[st], h)
        cursors[st] += h + 80
    start = dict.fromkeys(by_id, 0)
    end = dict.fromkeys(by_id, 0)
    for e in spec["edges"]:
        x, y, _ = slots[e["from"]]
        xx, yy, _ = slots[e["to"]]
        width = e["weight"] * scale
        a = y + start[e["from"]]
        b = yy + end[e["to"]]
        d = (
            f"M {x + 20:g} {a:g} C {x + 160:g} {a:g} {xx - 140:g} {b:g} "
            f"{xx:g} {b:g} L {xx:g} {b + width:g} C {xx - 140:g} {b + width:g} "
            f"{x + 160:g} {a + width:g} {x + 20:g} {a + width:g} Z"
        )
        out.append(path(d, "band"))
        start[e["from"]] += width
        end[e["to"]] += width
    for n in nodes:
        x, y, h = slots[n["id"]]
        out.extend([rect(x, y, 20, h, "solid", 0), text(x, y - 16, n["label"])])
    out.append(text(80, 60, "Band width = " + spec["unit"]))
    return 1640, max(900, 160 + len(nodes) * 190), "".join(out)


def render_geometry(spec):
    kind = spec["type"]
    if kind in GRAPHS:
        return graph(spec)
    if kind in {"tree", "org-chart", "nested", "layer-stack", "loop", "fishbone"}:
        return hierarchy(spec)
    if kind in {
        "quadrant",
        "radar",
        "polar",
        "pyramid",
        "treemap",
        "heatmap",
        "bar",
        "waterfall",
        "line",
        "scatter",
        "wardley",
    }:
        return charts(spec)
    return other(spec)
