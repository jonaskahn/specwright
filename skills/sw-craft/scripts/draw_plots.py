"""Quantitative drawings: every mark carries its value and source IDs directly."""

from __future__ import annotations

import math

from draw_layout import (
    Canvas,
    Placer,
    ids_text,
    measure,
    nice_ticks,
    squarify,
    tab_width,
    tick_text,
    wrap,
)


def d_cls(i):
    return f"d{min(i + 1, 8)}"


def signed(v):
    return f"{v:+g}".replace("-", "−")


def spread(values, gap):
    """Push sorted label centres apart so no two are closer than gap."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for a, b in zip(order, order[1:], strict=False):
        if out[b] - out[a] < gap:
            out[b] = out[a] + gap
    shift = (out[order[-1]] - values[order[-1]]) / 2 if order else 0
    return [v - shift for v in out]


def legend(cv, x, y, items):
    """Horizontal key strip: items are (kind, class, text)."""
    cursor = x
    for kind, cls, text in items:
        if kind == "rect":
            cv.rect(cursor, y - 6, 12, 12, cls, 2, "over")
            cursor += 18
        elif kind == "ring":
            cv.circle(cursor + 6, y, 6, cls, "over")
            cursor += 18
        elif kind == "dot":
            cv.circle(cursor + 6, y, 5, cls, "over")
            cursor += 18
        cv.text(cursor, y + 4, text, "small", size=13, layer="over")
        cursor += measure(text, 13) + 22


def y_axis(cv, x0, top, h, ticks, lo, hi, width):
    for t in ticks:
        y = top + h * (hi - t) / (hi - lo)
        cv.line(x0, y, x0 + width, y, "grid", "under")
        cv.text(x0 - 10, y + 4, tick_text(t), "small", "end", 13, layer="under")
    cv.line(x0, top, x0, top + h, "axis", "under")


def bar(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    dumb = spec.get("variant") == "dumbbell"
    vals = [n["value"] for n in nodes]
    comps = [n["compare"] for n in nodes] if dumb else []
    ticks, lo, hi = nice_ticks(0, max(vals + comps) or 1)
    lw = max(measure(n["label"], 15, bold=True) for n in nodes)
    x0, pw, top, rh = lw + 20, 520, 52, 44
    scale = pw / (hi - lo)
    cv.text(x0, 6, spec["unit"], "micro", layer="under", size=12)
    for t in ticks:
        x = x0 + (t - lo) * scale
        cv.line(x, top - 12, x, top + rh * len(nodes) - 8, "grid", "under")
        cv.text(x, top - 18, tick_text(t), "small", "middle", 13, layer="under")
    cv.line(x0, top - 12, x0, top + rh * len(nodes) - 8, "axis", "under")
    for i, n in enumerate(nodes):
        y = top + i * rh
        value, bx = n["value"], x0 + (n["value"] - lo) * scale
        out = [cv.ttext(x0 - 14, y + 22, n["label"], "node-name", "end", bold=True)]
        right = bx
        if dumb:
            cx = x0 + (n["compare"] - lo) * scale
            out.append(cv.tline(min(bx, cx), y + 16, max(bx, cx), y + 16, "edge"))
            out.append(cv.tcircle(bx, y + 16, 7, "series-1 mark"))
            out.append(cv.tcircle(cx, y + 16, 7, "hollow series-2"))
            right = max(bx, cx)
            out.append(
                cv.ttext(right + 14, y + 21, f"{value:g} / {n['compare']:g}", "value", bold=True)
            )
            end = right + 14 + measure(f"{value:g} / {n['compare']:g}", 15, bold=True)
        else:
            out.append(cv.trect(x0, y + 4, max(1, bx - x0), 24, f"series-1 enter {d_cls(i)}", 3))
            out.append(cv.ttext(bx + 8, y + 22, f"{value:g}", "value", bold=True))
            end = bx + 8 + measure(f"{value:g}", 15, bold=True)
        out.append(cv.chip(n, end + 10, y + 16))
        left, right = x0 - lw - 14, end + 10 + tab_width(n)
        cv.node(n, "".join(out), (left, y, right - left, rh - 8))
    if dumb:
        legend(
            cv,
            x0,
            top + rh * len(nodes) + 20,
            [("dot", "series-1", "value"), ("ring", "hollow series-2", "compare")],
        )
    return cv


def waterfall(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    levels, running = [], 0
    for n in nodes:
        start = 0 if n.get("total") else running
        end = n["value"] if n.get("total") else start + n["value"]
        levels.append((start, end))
        running = end
    ticks, lo, hi = nice_ticks(
        min(0, min(min(v) for v in levels)), max(0, max(max(v) for v in levels))
    )
    pitch = max(112, max(measure(n["label"], 15, bold=True) for n in nodes) / 2 + 24)
    pitch = min(pitch, 176)
    x0, top, height = 56, 40, 300
    yy = lambda v: top + height * (hi - v) / (hi - lo)  # noqa: E731
    cv.text(x0, 6, spec["unit"], "micro", layer="under", size=12)
    y_axis(cv, x0, top, height, ticks, lo, hi, pitch * len(nodes))
    cv.line(x0, yy(0), x0 + pitch * len(nodes), yy(0), "axis", "under")
    for i, (n, (a, b)) in enumerate(zip(nodes, levels, strict=True)):
        x = x0 + pitch * i + (pitch - 64) / 2
        total = bool(n.get("total"))
        cls = "total" if total else "up" if b >= a else "down"
        y_top, y_bot = min(yy(a), yy(b)), max(yy(a), yy(b))
        out = [cv.trect(x, y_top, 64, max(2, y_bot - y_top), f"{cls} enter {d_cls(i)}", 2)]
        text = f"{b:g}" if total else signed(b - a)
        if b >= a or total:
            out.append(cv.ttext(x + 32, y_top - 8, text, "value", "middle", bold=True))
        else:
            out.append(cv.ttext(x + 32, y_bot + 20, text, "value", "middle", bold=True))
        base = top + height + 22
        lines = wrap(n["label"], pitch - 16, 15, True)
        for k, line in enumerate(lines):
            out.append(cv.ttext(x + 32, base + 18 * k, line, "node-name", "middle", bold=True))
        out.append(cv.chip(n, x + 32 + tab_width(n) / 2, base + 18 * len(lines) + 4, "end"))
        cv.node(n, "".join(out), (x0 + pitch * i + 4, y_top - 30, pitch - 8, height + 80))
        if i < len(nodes) - 1:
            cv.line(x + 64, yy(b), x + pitch, yy(b), "rule", "under")
    legend(
        cv,
        x0,
        top + height + 22 + 18 * 3 + 34,
        [("rect", "up", "rises"), ("rect", "down", "falls"), ("rect", "total", "total")],
    )
    return cv


def _end_labels(cv, items, x, gap=20):
    """items: (node, y, series class); returns svg strings per node id."""
    ys = spread([y for _, y, _ in items], gap)
    out = {}
    for (n, _y0, _k), y in zip(items, ys, strict=True):
        text, _ = cv.label(n, x + 14, y)
        out[n["id"]] = text
    return out


def line_chart(spec):
    cv = Canvas()
    nodes, cats = spec["nodes"], spec["categories"]
    variant = spec.get("variant", "line")
    n_c = len(cats)
    pw = max(360, 130 * (n_c - 1)) if variant != "slopegraph" else 340
    x0, top, height = 72, 48, 300
    xs = [x0 + pw * j / (n_c - 1) for j in range(n_c)]
    cv.text(x0, 14, spec["unit"], "micro", layer="under", size=12)
    for j, c in enumerate(cats):
        cv.text(xs[j], top + height + 28, c, "small", "middle", 13, layer="under")
    vmax = max(v for n in nodes for v in n["values"]) or 1
    if variant == "streamgraph":
        vmax = max(sum(n["values"][j] for n in nodes) for j in range(n_c)) or 1
    ticks, lo, hi = nice_ticks(0, vmax)
    scale = height / (hi - lo)
    if variant in {"line", "slopegraph"}:
        if variant == "line":
            y_axis(cv, x0, top, height, ticks, lo, hi, pw)
        for x in xs:
            cv.line(x, top, x, top + height, "grid", "under")
    ends = []
    if variant == "bump":
        step = height / max(1, len(nodes) - 1)
        for r in range(len(nodes)):
            cv.text(x0 - 14, top + r * step + 4, str(r + 1), "small", "end", 13, layer="under")
            cv.line(x0, top + r * step, xs[-1], top + r * step, "grid", "under")
        cv.text(x0 - 14, top - 18, "Rank", "micro", "end", layer="under", size=12)
    previous = [0.0] * n_c
    groups = {}
    for i, n in enumerate(nodes):
        k = i % 5 + 1
        pts = []
        for j, v in enumerate(n["values"]):
            if variant == "bump":
                order = sorted(nodes, key=lambda m, j=j: (-m["values"][j], m["id"]))
                y = top + order.index(n) * height / max(1, len(nodes) - 1)
            elif variant == "ridgeline":
                y = top + 70 + i * 100 - 70 * v / vmax
            else:
                y = top + height - v * scale
            pts.append((xs[j], y))
        out = []
        if variant == "ridgeline":
            base = top + 70 + i * 100
            cv.line(x0, base, xs[-1], base, "grid", "under")
            poly = pts + [(xs[j], base) for j in reversed(range(n_c))]
            out.append(cv.tpoly(poly, f"area series-{k}"))
            end_y = base
        elif variant == "streamgraph":
            tops, bots = [], []
            for j in range(n_c):
                total = sum(m["values"][j] for m in nodes)
                start = top + height / 2 - total * scale / 2 + previous[j] * scale
                tops.append((xs[j], start))
                bots.append((xs[j], start + n["values"][j] * scale))
            previous = [a + b for a, b in zip(previous, n["values"], strict=True)]
            out.append(cv.tpoly(tops + bots[::-1], f"area series-{k}"))
            end_y = (tops[-1][1] + bots[-1][1]) / 2
        else:
            d = "M " + " L ".join(f"{px:g} {py:g}" for px, py in pts)
            out.append(cv.tpath(d, f"line-{k}", pts))
            for j, (px, py) in enumerate(pts):
                out.append(cv.tcircle(px, py, 4, f"series-{k} pop {d_cls(j)}"))
            end_y = pts[-1][1]
        ends.append((n, end_y, k))
        groups[n["id"]] = out
    if variant == "slopegraph":
        for n, _y, _k in ends:
            ly = n["values"][0]
            groups[n["id"]].append(
                cv.ttext(
                    xs[0] - 14,
                    top + height - ly * scale + 5,
                    f"{n['label']} {ly:g}",
                    "value",
                    "end",
                    bold=True,
                )
            )
    tails = _end_labels(cv, ends, xs[-1] + 4)
    for n in nodes:
        cv.node(n, "".join(groups[n["id"]]) + tails[n["id"]])
    return cv


def _spread_rects(placer, rects):
    for r in rects:
        placer.reserve(r)


def scatter_like(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    kind, variant = spec["type"], spec.get("variant", "scatter")
    x0, y0, w, h = 72, 48, 560, 400
    cv.text(x0, 18, spec["y_axis"] + " ↑", "micro", layer="under", size=12)
    cv.text(x0 + w, y0 + h + 46, spec["x_axis"] + " →", "micro", "end", layer="under", size=12)
    for t in (0, 0.25, 0.5, 0.75, 1):
        cv.line(x0, y0 + h * (1 - t), x0 + w, y0 + h * (1 - t), "grid", "under")
        cv.line(x0 + w * t, y0, x0 + w * t, y0 + h, "grid", "under")
        cv.text(x0 - 10, y0 + h * (1 - t) + 4, tick_text(t), "small", "end", 13, layer="under")
        cv.text(x0 + w * t, y0 + h + 24, tick_text(t), "small", "middle", 13, layer="under")
    cv.line(x0, y0 + h, x0 + w, y0 + h, "axis", "under")
    cv.line(x0, y0, x0, y0 + h, "axis", "under")
    if kind == "quadrant":
        cv.line(x0 + w / 2, y0, x0 + w / 2, y0 + h, "rule dashed", "under")
        cv.line(x0, y0 + h / 2, x0 + w, y0 + h / 2, "rule dashed", "under")
    placer = Placer()
    points = []
    for n in nodes:
        if variant == "box-plot":
            continue
        px, py = x0 + w * n["x"], y0 + h * (1 - n["y"])
        r = math.sqrt(n["size"]) * 1.4 if variant == "bubble" else 7
        points.append((n, px, py, r))
    if variant == "beeswarm":
        used = {}
        moved = []
        for n, _px, _py, r in points:
            bin_ = round(n["x"] * 20)
            slot = used.get(bin_, 0)
            used[bin_] = slot + 1
            offset = (slot + 1) // 2 * (1 if slot % 2 else -1)
            moved.append((n, x0 + w * bin_ / 20, y0 + h / 2 + offset * 26, r))
        points = moved
    for _n, px, py, r in points:
        placer.reserve((px - r - 2, py - r - 2, 2 * r + 4, 2 * r + 4))
    if variant == "box-plot":
        step = h / len(nodes)
        for i, n in enumerate(nodes):
            lo_, q1, med, q3, hi_ = n["samples"]
            y = y0 + step * i + step / 2
            xs = [x0 + w * v for v in (lo_, q1, med, q3, hi_)]
            out = [
                cv.tline(xs[0], y, xs[4], y, "edge"),
                cv.tline(xs[0], y - 8, xs[0], y + 8, "edge"),
                cv.tline(xs[4], y - 8, xs[4], y + 8, "edge"),
                cv.trect(xs[1], y - 14, xs[3] - xs[1], 28, "series-1 area", 3),
                cv.tline(xs[2], y - 14, xs[2], y + 14, "edge mark"),
            ]
            text, _ = cv.label(n, xs[0], y - 26)
            cv.node(n, "".join(out) + text)
        return cv
    for n, px, py, r in points:
        cls = "series-1" if n.get("focal") is not True else "series-4"
        mark = cv.tcircle(px, py, r, f"{cls} halo" if False else cls, 'stroke-width="2"')
        wl = measure(n["label"], 15, bold=True) + (tab_width(n) + 8 if tab_width(n) else 0)
        anchors = [
            (px + r + 8, py - 10),
            (px - r - 8 - wl, py - 10),
            (px - wl / 2, py - r - 32),
            (px - wl / 2, py + r + 10),
        ]
        rect = placer.place(wl, 20, anchors)
        text, _ = cv.label(n, rect[0], rect[1] + 10, "start", halo=True)
        cv.node(n, mark + text)
    return cv


def wardley(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    x0, y0, w, h = 72, 48, 640, 420
    stages = ["Genesis", "Custom-built", "Product", "Commodity"]
    cv.text(x0, 18, "Visibility ↑", "micro", layer="under", size=12)
    for i, s in enumerate(stages):
        cv.line(x0 + w * i / 4, y0, x0 + w * i / 4, y0 + h, "grid", "under")
        cv.text(x0 + w * (i + 0.5) / 4, y0 + h + 26, s, "micro", "middle", layer="under", size=12)
    cv.text(x0 + w, y0 + h + 52, "Evolution →", "micro", "end", layer="under", size=12)
    cv.line(x0, y0 + h, x0 + w, y0 + h, "axis", "under")
    cv.line(x0, y0, x0, y0 + h, "axis", "under")
    pos = {n["id"]: (x0 + w * n["evolution"], y0 + h * (1 - n["visibility"])) for n in nodes}
    for e in spec.get("edges", []):
        (ax, ay), (bx, by) = pos[e["from"]], pos[e["to"]]
        end_x = bx - 10 if bx >= ax else bx + 10
        cv.path(
            f"M {ax:g} {ay:g} V {by:g} H {end_x:g}",
            "edge",
            "edges",
            'marker-end="url(#arrow)"',
            (min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)),
        )
    placer = Placer()
    for px, py in pos.values():
        placer.reserve((px - 9, py - 9, 18, 18))
    for n in nodes:
        px, py = pos[n["id"]]
        wl = measure(n["label"], 15, bold=True) + (tab_width(n) + 8 if tab_width(n) else 0)
        rect = placer.place(
            wl,
            20,
            [
                (px + 14, py - 10),
                (px - 14 - wl, py - 10),
                (px - wl / 2, py + 12),
                (px - wl / 2, py - 32),
            ],
        )
        text, _ = cv.label(n, rect[0], rect[1] + 10, "start", halo=True)
        cls = "series-4" if n.get("focal") is True else "series-1"
        cv.node(n, cv.tcircle(px, py, 8, f"{cls} mark", 'stroke-width="2"') + text)
    return cv


def radar(spec):
    cv = Canvas()
    nodes, axes_ = spec["nodes"], spec["axes"]
    cx, cy, R, mx = 360, 300, 220, spec["maximum"]
    n_a = len(axes_)
    ang = lambda j: -math.pi / 2 + j * 2 * math.pi / n_a  # noqa: E731
    for f in (0.25, 0.5, 0.75, 1):
        pts = [(cx + R * f * math.cos(ang(j)), cy + R * f * math.sin(ang(j))) for j in range(n_a)]
        cv.poly(pts, "frame", "under")
        cv.text(cx + 6, cy - R * f - 4, tick_text(mx * f), "small halo", size=13, layer="under")
    for j, name in enumerate(axes_):
        x, y = cx + R * math.cos(ang(j)), cy + R * math.sin(ang(j))
        cv.line(cx, cy, x, y, "grid", "under")
        lx, ly = cx + (R + 24) * math.cos(ang(j)), cy + (R + 24) * math.sin(ang(j))
        anchor = (
            "middle" if abs(math.cos(ang(j))) < 0.3 else "start" if math.cos(ang(j)) > 0 else "end"
        )
        cv.text(lx, ly + 5, name, "node-name", anchor, layer="under", bold=True)
    for i, n in enumerate(nodes):
        k = i % 5 + 1
        pts = [
            (cx + R * v / mx * math.cos(ang(j)), cy + R * v / mx * math.sin(ang(j)))
            for j, v in enumerate(n["values"])
        ]
        out = [cv.tpoly(pts, f"area series-{k}")]
        out += [cv.tcircle(px, py, 4, f"series-{k}") for px, py in pts]
        ly = 40 + i * 28
        out.append(cv.tcircle(cx + R + 140, ly, 5, f"series-{k}"))
        text, _ = cv.label(n, cx + R + 154, ly)
        cv.node(n, "".join(out) + text)
    return cv


def polar(spec):
    cv = Canvas()
    nodes, mx = spec["nodes"], spec["maximum"]
    cx, cy, R = 360, 340, 220
    n = len(nodes)
    for f in (0.25, 0.5, 0.75, 1):
        cv.circle(cx, cy, R * f, "frame", "under")
        cv.text(cx + 6, cy - R * f - 4, tick_text(mx * f), "small", size=13, layer="under")
    for i, node in enumerate(nodes):
        a = -math.pi / 2 + i * 2 * math.pi / n
        r = R * node["value"] / mx
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        cv.line(cx, cy, cx + R * math.cos(a), cy + R * math.sin(a), "grid", "under")
        out = [
            cv.tline(cx, cy, x, y, "line-1" if False else "edge mark"),
            cv.tcircle(x, y, 7, "series-1"),
        ]
        lx, ly = cx + (R + 22) * math.cos(a), cy + (R + 22) * math.sin(a)
        anchor = "middle" if abs(math.cos(a)) < 0.3 else "start" if math.cos(a) > 0 else "end"
        text, _ = cv.label(node, lx, ly, anchor, value=f"{node['value']:g}")
        cv.node(node, "".join(out) + text)
    return cv


def pyramid(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    funnel = spec.get("variant") == "funnel"
    n = len(nodes)
    mx = max(v["value"] for v in nodes) or 1
    cx, top, th, gap = 300, 24, 60, 6
    label_x = 660
    for i, node in enumerate(nodes):
        y = top + i * (th + gap)
        step = f"ramp-{min(5, 1 + int(4 * i / max(1, n - 1)))}"
        if funnel:
            w = 560 * node["value"] / mx
            shape = cv.tpoly(
                [(cx - w / 2, y), (cx + w / 2, y), (cx + w / 2, y + th), (cx - w / 2, y + th)],
                f"{step} enter {d_cls(i)}",
            )
        else:
            w0, w1 = 120 + i * 480 / n, 120 + (i + 1) * 480 / n
            shape = cv.tpoly(
                [(cx - w0 / 2, y), (cx + w0 / 2, y), (cx + w1 / 2, y + th), (cx - w1 / 2, y + th)],
                step,
            )
        edge = (cx + (w if funnel else w1) / 2) + 14
        lead = cv.tline(edge, y + th / 2, label_x - 14, y + th / 2, "grid")
        text, _ = cv.label(node, label_x, y + th / 2, "start", value=f"{node['value']:g}")
        cv.node(node, shape + lead + text)
    cv.text(label_x, top - 8, spec["unit"], "micro", size=12)
    return cv


def _cell_text(cv, node, x, y, w, h, tx):
    lines = wrap(node["label"], w - 20, 15, True)
    out = [
        cv.ttext(x + 12, y + 24 + 20 * k, line, f"node-name {tx}", bold=True)
        for k, line in enumerate(lines)
    ]
    value_y = y + 24 + 20 * len(lines) + 4
    out.append(cv.ttext(x + 12, value_y, f"{node['value']:g}", f"value {tx}", bold=True))
    text = ids_text(node)
    if text:
        cw = tab_width(node)
        if cw + 16 <= w:
            out.append(cv.chip(node, x + w - 8, y + h - 14, "end"))
        else:
            out.append(cv.ttext(x + 12, y + h - 10, text, f"ids {tx}", mono=True))
    return "".join(out)


def treemap(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    area = (0, 24, 760, 400)
    cv.text(0, 8, spec["unit"], "micro", layer="under", size=12)
    if spec.get("variant") == "marimekko":
        total = sum(n["value"] for n in nodes)
        left = area[0]
        for n in nodes:
            w = area[2] * n["value"] / total
            segs = n["segments"]
            bottom = area[1] + area[3]
            out = []
            for j, v in enumerate(segs):
                hh = area[3] * v / sum(segs)
                out.append(cv.trect(left, bottom - hh, w, hh, f"series-{j % 5 + 1} area", 0))
                if hh >= 20:
                    out.append(
                        cv.ttext(
                            left + w / 2,
                            bottom - hh / 2 + 5,
                            f"{v:g}",
                            "value",
                            "middle",
                            bold=True,
                        )
                    )
                bottom -= hh
            head, _ = cv.label(n, left + 4, area[1] - 14, "start", value=f"{n['value']:g}")
            cv.node(n, "".join(out) + head, (left, area[1], w, area[3]))
            left += w
        legend(
            cv,
            0,
            area[1] + area[3] + 28,
            [
                ("rect", f"series-{j % 5 + 1}", f"segment {j + 1}")
                for j in range(max(len(n["segments"]) for n in nodes))
            ],
        )
        return cv
    rects = squarify([n["value"] for n in nodes], *area)
    mx = max(n["value"] for n in nodes)
    for n, (x, y, w, h) in zip(nodes, rects, strict=True):
        step = min(5, 1 + int(4 * n["value"] / mx))
        body = cv.trect(x + 1, y + 1, w - 2, h - 2, f"ramp-{step}", 4)
        cv.node(
            n,
            body + _cell_text(cv, n, x + 1, y + 1, w - 2, h - 2, f"rt-{step}"),
            (x + 1, y + 1, w - 2, h - 2),
        )
    return cv


def heatmap(spec):
    cv = Canvas()
    nodes, rows, cols = spec["nodes"], spec["rows"], spec["columns"]
    mx = max(n["value"] for n in nodes) or 1
    cw, ch, lw = 148, 92, max(measure(r, 15, bold=True) for r in spec["rows"]) + 16
    x0, y0 = lw, 40
    cv.text(0, 8, spec["unit"], "micro", layer="under", size=12)
    for j, c in enumerate(cols):
        cv.text(
            x0 + j * (cw + 6) + cw / 2, y0 - 12, c, "node-name", "middle", layer="under", bold=True
        )
    for i, r in enumerate(rows):
        cv.text(
            x0 - 12, y0 + i * (ch + 6) + ch / 2 + 5, r, "node-name", "end", layer="under", bold=True
        )
        for j, c in enumerate(cols):
            if not any(n["row"] == r and n["column"] == c for n in nodes):
                cv.rect(x0 + j * (cw + 6), y0 + i * (ch + 6), cw, ch, "ghost", 4, "under")
    for n in nodes:
        x = x0 + cols.index(n["column"]) * (cw + 6)
        y = y0 + rows.index(n["row"]) * (ch + 6)
        step = min(5, 1 + int(4 * n["value"] / mx))
        body = cv.trect(x, y, cw, ch, f"ramp-{step}", 4)
        cv.node(n, body + _cell_text(cv, n, x, y, cw, ch, f"rt-{step}"), (x, y, cw, ch))
    ly = y0 + len(rows) * (ch + 6) + 22
    cv.text(x0, ly + 4, "0", "small", "start", 13, layer="over")
    for s in range(5):
        cv.rect(x0 + 24 + s * 28, ly - 7, 28, 14, f"ramp-{s + 1}", 2, "over")
    cv.text(
        x0 + 24 + 5 * 28 + 8, ly + 4, f"{mx:g} {spec['unit']}", "small", "start", 13, layer="over"
    )
    return cv


def sankey(spec):
    cv = Canvas()
    nodes, edges = spec["nodes"], spec["edges"]
    by = {n["id"]: n for n in nodes}
    totals = {
        n["id"]: max(
            sum(e["weight"] for e in edges if e["from"] == n["id"]),
            sum(e["weight"] for e in edges if e["to"] == n["id"]),
        )
        for n in nodes
    }
    stages = sorted({n["stage"] for n in nodes})
    stage_sum = {s: sum(totals[n["id"]] for n in nodes if n["stage"] == s) for s in stages}
    scale = 280 / max(stage_sum.values())
    colw, bar_w = 260, 16
    pos, cursors = {}, dict.fromkeys(stages, 40)
    for n in nodes:
        s = n["stage"]
        hgt = max(6, totals[n["id"]] * scale)
        pos[n["id"]] = (stages.index(s) * colw, cursors[s], hgt)
        cursors[s] += hgt + 36
    out_off, in_off = dict.fromkeys(by, 0.0), dict.fromkeys(by, 0.0)
    cv.text(0, 8, f"Band width = {spec['unit']}", "micro", layer="under", size=12)
    for e in edges:
        x, y, _ = pos[e["from"]]
        xx, yy, _ = pos[e["to"]]
        wd = e["weight"] * scale
        a, b = y + out_off[e["from"]], yy + in_off[e["to"]]
        c1, c2 = x + colw / 2 + 40, xx - colw / 2 + 40 + bar_w
        d = (
            f"M {x + bar_w:g} {a:g} C {c1:g} {a:g} {c2:g} {b:g} {xx:g} {b:g} "
            f"L {xx:g} {b + wd:g} C {c2:g} {b + wd:g} {c1:g} {a + wd:g} "
            f"{x + bar_w:g} {a + wd:g} Z"
        )
        k = list(by).index(e["from"]) % 5 + 1
        cv.path(
            d,
            f"band series-{k} enter {d_cls(stages.index(by[e['from']]['stage']))}",
            "edges",
            box=(x, a, xx - x, wd),
        )
        if wd >= 18:
            cv.text(
                (x + bar_w + xx) / 2,
                (a + b) / 2 + wd / 2 + 5,
                f"{e['weight']:g}",
                "value halo",
                "middle",
                layer="tickets",
                bold=True,
            )
        out_off[e["from"]] += wd
        in_off[e["to"]] += wd
    for n in nodes:
        x, y, hgt = pos[n["id"]]
        text, _ = cv.label(n, x, y - 14, "start", halo=True)
        cv.node(n, cv.trect(x, y, bar_w, hgt, "total", 2) + text, (x, y, bar_w, hgt))
    return cv


def build(spec):
    kind = spec["type"]
    return {
        "bar": bar,
        "waterfall": waterfall,
        "line": line_chart,
        "scatter": scatter_like,
        "quadrant": scatter_like,
        "wardley": wardley,
        "radar": radar,
        "polar": polar,
        "pyramid": pyramid,
        "treemap": treemap,
        "heatmap": heatmap,
        "sankey": sankey,
    }[kind](spec)
