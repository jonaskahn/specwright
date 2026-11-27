"""Containment, cycle, board, set and calendar drawings."""

from __future__ import annotations

import math
from datetime import date, timedelta

from draw_common import esc
from draw_graphs import card_dims, draw_card
from draw_layout import Canvas, Placer, ceil4, glyph, measure, num, overlaps, tab_width, wrap
from draw_plots import d_cls, legend

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def nested(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    kids = {n["id"]: [] for n in nodes}
    for n in nodes:
        if n.get("parent"):
            kids[n["parent"]].append(n)
    root = next(n for n in nodes if not n.get("parent"))

    def size(n):
        own = measure(n["label"], 15, bold=True) + 32 + max(tab_width(n), 0)
        if not kids[n["id"]]:
            return max(220, ceil4(own)), 56
        parts = [size(c) for c in kids[n["id"]]]
        return max(ceil4(own), max(p[0] for p in parts) + 32), 44 + sum(
            p[1] + 12 for p in parts
        ) + 4

    def draw(n, x, y, depth):
        w, h = size(n)
        cls = "focal" if n.get("focal") is True else "box" if depth % 2 == 0 else "lane"
        body = [cv.trect(x, y, w, h, cls, 8 if kids[n["id"]] else 6)]
        body.append(cv.ttext(x + 16, y + 26, n["label"], "node-name", bold=True))
        body.append(cv.tab(n, x + w - 12, y))
        leaf = not kids[n["id"]]
        cv.node(n, "".join(body), (x, y, w, h) if leaf else None)
        cy = y + 44
        for c in kids[n["id"]]:
            cw = size(c)[0]
            draw(c, x + (w - max(cw, w - 32)) / 2 if False else x + 16, cy, depth + 1)
            cy += size(c)[1] + 12

    # Children fill their parent's width so every boundary stays visibly nested.
    def fit(n, x, y, depth, width):
        h = size(n)[1]
        cls = "focal" if n.get("focal") is True else "box" if depth % 2 == 0 else "lane"
        body = [
            cv.trect(x, y, width, h, cls, 8 if kids[n["id"]] else 6),
            cv.ttext(x + 16, y + 26, n["label"], "node-name", bold=True),
            cv.tab(n, x + width - 12, y),
        ]
        cv.node(n, "".join(body), None if kids[n["id"]] else (x, y, width, h))
        cy = y + 44
        for c in kids[n["id"]]:
            fit(c, x + 16, cy, depth + 1, width - 32)
            cy += size(c)[1] + 12

    _ = draw
    fit(root, 0, 0, 0, size(root)[0])
    return cv


def layer_stack(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    width = max(
        560,
        max(measure(n["label"], 15, True) + 90 + tab_width(n) for n in nodes),
        max(measure(n["responsibility"], 13) + 90 for n in nodes),
    )
    for i, n in enumerate(nodes):
        y = i * 84
        cls = "box focal" if n.get("focal") is True else "box"
        body = [
            cv.trect(0, y, width, 72, cls, 6),
            cv.tcircle(32, y + 36, 14, "hollow"),
            cv.ttext(32, y + 41, str(i + 1), "value", "middle", bold=True),
            cv.ttext(64, y + 32, n["label"], "node-name", bold=True),
            cv.ttext(64, y + 54, n["responsibility"], "small", size=13),
            cv.tab(n, width - 12, y),
        ]
        cv.node(n, "".join(body), (0, y, width, 72))
    return cv


def loop(spec):
    cv = Canvas()
    nodes, edges = spec["nodes"], spec["edges"]
    n = len(nodes)
    pill = max(measure(e["label"], 13) + 24 for e in edges)
    R = max(150, (pill + 90) * n / (2 * math.pi))
    r = 22
    ang = {nd["id"]: -math.pi / 2 + i * 2 * math.pi / n for i, nd in enumerate(nodes)}
    delta = (r + 10) / R
    for e in edges:
        a, b = ang[e["from"]], ang[e["to"]]
        if b <= a:
            b += 2 * math.pi
        p = (R * math.cos(a + delta), R * math.sin(a + delta))
        q = (R * math.cos(b - delta), R * math.sin(b - delta))
        large = 1 if (b - a - 2 * delta) > math.pi else 0
        d = f"M {p[0]:.2f} {p[1]:.2f} A {R:g} {R:g} 0 {large} 1 {q[0]:.2f} {q[1]:.2f}"
        cv.path(d, "edge", "edges", 'marker-end="url(#arrow)"', (-R, -R, 2 * R, 2 * R))
        mid = (a + b) / 2
        mx_, my_ = R * math.cos(mid), R * math.sin(mid)
        pw = measure(e["label"], 13) + 20
        cv.put(
            "tickets",
            f'<rect x="{num(mx_ - pw / 2)}" y="{num(my_ - 11)}" width="{num(pw)}" height="22" '
            f'rx="11" class="ticket"/><text x="{num(mx_)}" y="{num(my_ + 4)}" class="small" '
            f'text-anchor="middle">{esc(e["label"])}</text>',
            (mx_ - pw / 2, my_ - 11, pw, 22),
        )
        cv.ticket_rects.append((mx_ - pw / 2, my_ - 11, pw, 22))
        cv.flows.append((d, R * (b - a - 2 * delta), e["to"]))
    for i, nd in enumerate(nodes):
        a = ang[nd["id"]]
        x, y = R * math.cos(a), R * math.sin(a)
        cls = "focal" if nd.get("focal") is True else "hollow"
        body = [
            cv.tcircle(x, y, r, cls),
            cv.ttext(x, y + 5, str(i + 1), "value", "middle", bold=True),
        ]
        c = math.cos(a)
        anchor = "middle" if abs(c) < 0.3 else "start" if c > 0 else "end"
        lx, ly = (R + r + 18) * math.cos(a), (R + r + 18) * math.sin(a)
        if abs(c) < 0.3:
            ly += 14 if math.sin(a) > 0 else -4
        text, _w = cv.label(nd, lx, ly, anchor)
        cv.node(nd, "".join(body) + text, (x - r, y - r, 2 * r, 2 * r))
    return cv


def fishbone(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    cats = list(dict.fromkeys(n["category"] for n in nodes))
    twig = (
        max(
            measure(n["label"], 15, True) + (tab_width(n) + 8 if tab_width(n) else 0) for n in nodes
        )
        + 24
    )
    pitch = max(150, twig + 56)
    per_cat = {c: [n for n in nodes if n["category"] == c] for c in cats}
    reach = max(len(v) for v in per_cat.values())
    arm = 60 + 34 * reach
    mid = arm + 40
    x_end = 40 + pitch * (math.ceil(len(cats) / 2)) + twig
    for ci, cat in enumerate(cats):
        side = -1 if ci % 2 == 0 else 1
        x = twig + 40 + (ci // 2) * pitch
        y_end = mid + side * arm
        cv.line(x, mid, x, y_end, "edge", "edges")
        hw = max(110, measure(cat, 15, True) + 28)
        head_y = y_end - 30 if side < 0 else y_end
        cv.rect(x - hw / 2, head_y, hw, 30, "box", 4, "nodes")
        cv.text(x, head_y + 20, cat, "node-name", "middle", bold=True)
        for k, n in enumerate(per_cat[cat]):
            yt = mid + side * (46 + 34 * k)
            tw = measure(n["label"], 15, True) + (tab_width(n) + 8 if tab_width(n) else 0) + 16
            body = [cv.tline(x - tw, yt, x, yt, "edge")]
            text, _w = cv.label(n, x - tw + 4, yt - 12, "start")
            cv.node(n, "".join(body) + text, (x - tw, yt - 24, tw, 28))
    cv.path(
        f"M 0 {mid} H {x_end}", "edge", "edges", 'marker-end="url(#arrow)"', (0, mid - 1, x_end, 2)
    )
    lines = wrap(spec["effect"], 200, 15, True)
    ew = max(measure(line, 15, True) for line in lines) + 32
    eh = 24 + 22 * len(lines)
    cv.rect(x_end, mid - eh / 2, ew, eh, "focal", 6, "nodes")
    for k, line in enumerate(lines):
        cv.text(x_end + 16, mid - eh / 2 + 28 + 22 * k, line, "node-name", bold=True)
    return cv


STATE_MARK = {
    "queued": ("square", "mk-stop"),
    "doing": ("diamond", "mk-run"),
    "blocked": ("triangle", "mk-fail"),
    "waiting": ("square", "mk-stop"),
    "done": ("circle", "mk-ok"),
}


def state_glyph(state, x, y):
    shape, cls = STATE_MARK[state]
    return glyph(shape, x, y, cls, 5)


def kanban(spec):
    cv = Canvas()
    cols, nodes = spec["columns"], spec["nodes"]
    limits = spec.get("limits", {})
    dims = {n["id"]: card_dims(n, [f"{n['state'].upper()} · {n['owner']}"]) for n in nodes}
    cw = max(d[0] for d in dims.values()) + 24
    gap = 16
    head = 72
    for i, c in enumerate(cols):
        members = [n for n in nodes if n["column"] == c]
        count, limit = len(members), limits.get(c)
        over = bool(limit and count > limit)
        x = i * (cw + gap)
        bottom = head + sum(dims[n["id"]][1] + 14 for n in members) + 6
        cv.rect(x, 0, cw, max(bottom, 120), "lane", 8, "under")
        cv.text(
            x + 14,
            28,
            f"{c} · {count}" + (f"/{limit}" if limit else ""),
            "micro",
            layer="under",
            size=12,
        )
        if over:
            cv.add("under", glyph("triangle", x + 20, 46, "mk-fail", 5))
            cv.text(x + 36, 51, "OVER LIMIT", "micro", layer="under", size=12)
        y = head
        for n in members:
            h = dims[n["id"]][1]
            mark = state_glyph(n["state"], x + 36, y + h - 15)
            label = (
                f'<text x="{num(x + 50)}" y="{num(y + h - 10)}" class="small">'
                f"{esc(n['state'].upper())} · {esc(n['owner'])}</text>"
            )
            cls = "box fail-box" if n["state"] == "blocked" else None
            draw_card(cv, n, x + 12, y, cw - 24, h, [], None, "node", mark + label, cls=cls)
            y += h + 14
    return cv


def venn(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    n = len(nodes)
    R = 140
    centers = (
        [(R, R + 40), (R + 120, R + 40)]
        if n == 2
        else [(R, R + 40), (R + 120, R + 40), (R + 60, R + 40 + 104)]
        if n == 3
        else [(R, R + 40)]
    )
    sets = [set(nd["members"]) for nd in nodes]
    for i, nd in enumerate(nodes):
        cx, cy = centers[i]
        k = i % 5 + 1
        label_y = cy - R - 14 if i < 2 or n < 3 else cy + R + 24
        text, _w = cv.label(nd, cx, label_y, "middle")
        cv.node(nd, cv.tcircle(cx, cy, R, f"set series-{k}") + text)
    members = sorted(set().union(*sets))
    # Region counts sit at the centroid of each exclusive region.
    regions = {}
    for gx in range(0, 500, 6):
        for gy in range(0, 500, 6):
            key = tuple(math.hypot(gx - c[0], gy - c[1]) <= R - 6 for c in centers)
            if any(key):
                regions.setdefault(key, []).append((gx, gy))
    for key, pts in regions.items():
        count = sum(all((m in sets[i]) == key[i] for i in range(n)) for m in members)
        if count:
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            cv.text(cx, cy + 6, str(count), "value halo", "middle", size=20, bold=True)
    top = max(c[1] for c in centers) + R + 56
    cv.text(0, top, "Membership", "micro", size=12)
    colw = [max(measure(nd["label"], 13), 40) + 20 for nd in nodes]
    mw = max(measure(m, 15) for m in members) + 24
    x = mw
    for i, nd in enumerate(nodes):
        cv.text(x + colw[i] / 2, top + 26, nd["label"], "small", "middle", 13)
        x += colw[i]
    for r, m in enumerate(members):
        y = top + 54 + r * 28
        cv.text(0, y + 5, m, "node-name", bold=True)
        x = mw
        for i in range(n):
            if m in sets[i]:
                cv.circle(x + colw[i] / 2, y, 6, f"series-{i % 5 + 1}")
            else:
                cv.text(x + colw[i] / 2, y + 5, "—", "small", "middle", 13)
            x += colw[i]
    return cv


def _month_ticks(lo, hi):
    ticks, cur = [], date(lo.year, lo.month, 1)
    while cur <= hi:
        if cur >= lo:
            ticks.append((cur, f"{MONTHS[cur.month - 1]} {cur.year}"))
        cur = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
    return ticks


def _ticks(lo, hi):
    span = (hi - lo).days
    if span >= 75:
        ticks = _month_ticks(lo, hi)
        if ticks:
            return ticks
    step = 1 if span <= 14 else 7
    out, cur = [], lo
    while cur <= hi:
        out.append((cur, f"{MONTHS[cur.month - 1]} {cur.day}"))
        cur += timedelta(days=step)
    return out


def timeline(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    dates = [date.fromisoformat(n["date"]) for n in nodes]
    lo, hi = min(dates), max(dates)
    span = max(1, (hi - lo).days)
    pw, axis = 760, 270
    xx = lambda d: (d - lo).days / span * pw  # noqa: E731
    cv.line(0, axis, pw, axis, "axis", "under")
    for d, text in _ticks(lo, hi):
        cv.line(xx(d), axis - 5, xx(d), axis + 5, "axis", "under")
        cv.text(xx(d), axis + 24, text, "small", "middle", 13, layer="under")
    placer = Placer()
    levels = [44, 92, 140, 188, 236]
    # Right to left: a label extends rightwards, so it may only span later events' stems
    # when it sits above them; the nearest free level then never crosses a stem.
    for i, (n, d) in enumerate(
        sorted(zip(nodes, dates, strict=True), key=lambda p: -p[1].toordinal())
    ):
        x = xx(d)
        w = (
            measure(n["label"], 15, True)
            + 8
            + measure(n["date"], 15, True)
            + (tab_width(n) + 8 if tab_width(n) else 0)
            + 12
        )
        level = levels[-1]
        for candidate in levels:
            label_rect = (x + 6, axis - candidate - 14, w, 24)
            stem_rect = (x - 2, axis - candidate - 14, 4, candidate + 14)
            if not any(
                overlaps(label_rect, o, 4) or overlaps(stem_rect, o, 4) for o in placer.rects
            ):
                level = candidate
                break
        placer.reserve((x + 6, axis - level - 14, w, 24))
        placer.reserve((x - 2, axis - level - 14, 4, level + 14))
        y = axis - level
        stem = cv.tline(x, axis, x, y, "edge")
        dot = cv.tcircle(x, axis, 6, f"series-1 pop {d_cls(i)}")
        text, _w = cv.label(n, x + 8, y, "start", value=n["date"])
        cv.node(n, stem + dot + text)
    return cv


def gantt(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    starts = [date.fromisoformat(n["start"]) for n in nodes]
    ends = [date.fromisoformat(n["end"]) for n in nodes]
    lo, hi = min(starts), max(ends) + timedelta(days=1)
    span = max(1, (hi - lo).days)
    lw = max(measure(n["label"], 15, True) for n in nodes)
    x0, pw, top, rh = lw + 20, 560, 44, 48
    xx = lambda d: x0 + (d - lo).days / span * pw  # noqa: E731
    for d, text in _ticks(lo, hi):
        cv.line(xx(d), top - 10, xx(d), top + rh * len(nodes), "grid", "under")
        cv.text(xx(d), top - 18, text, "small", "middle", 13, layer="under")
    cv.line(x0, top - 10, x0, top + rh * len(nodes), "axis", "under")
    for i, (n, s, e) in enumerate(zip(nodes, starts, ends, strict=True)):
        y = top + i * rh
        x, x2 = xx(s), xx(e + timedelta(days=1))
        span_text = f"{n['start']} → {n['end']}"
        out = [
            cv.ttext(x0 - 14, y + 26, n["label"], "node-name", "end", bold=True),
            cv.trect(x, y + 8, max(4, x2 - x), 26, f"series-1 enter {d_cls(i)}", 3),
            cv.ttext(max(x2, x + 4) + 10, y + 26, span_text, "small", size=13),
        ]
        out.append(cv.chip(n, max(x2, x + 4) + 10 + measure(span_text, 13) + 10, y + 21))
        cv.node(n, "".join(out), (x0 - lw - 14, y, lw + 14 + pw, rh - 6))
    return cv


MATRIX = {
    "allow": ("mk-ok", "Allow"),
    "deny": ("mk-fail", "Deny"),
    "unknown": ("mk-run", "Unknown"),
}


def matrix(spec):
    cv = Canvas()
    nodes, cols = spec["nodes"], spec["columns"]
    lw = max(measure(n["label"], 15, True) + tab_width(n) + 24 for n in nodes)
    cw, rh, top = 148, 52, 40
    for j, c in enumerate(cols):
        cv.text(lw + j * cw + cw / 2, top - 14, c, "node-name", "middle", bold=True, layer="under")
    for i, n in enumerate(nodes):
        y = top + i * rh
        text, _w = cv.label(n, 0, y + rh / 2 - 4)
        out = [text]
        for j, value in enumerate(n["permissions"]):
            cls, word = MATRIX[value]
            x = lw + j * cw
            box = {"deny": "fail-box", "unknown": "ghost"}.get(value, "box")
            out.append(cv.trect(x + 4, y, cw - 8, rh - 8, box, 6))
            gx, gy = x + 28, y + (rh - 8) / 2
            if value == "allow":
                out.append(cv.tcircle(gx, gy, 6, cls))
            elif value == "deny":
                out.append(cv.tpoly([(gx, gy - 7), (gx + 7, gy + 6), (gx - 7, gy + 6)], cls))
            else:
                out.append(cv.tpoly([(gx, gy - 7), (gx + 7, gy), (gx, gy + 7), (gx - 7, gy)], cls))
            out.append(cv.ttext(x + 46, gy + 5, word, "node-name", bold=True))
        cv.node(n, "".join(out), (0, y, lw + cw * len(cols), rh - 8))
    legend(
        cv,
        0,
        top + rh * len(nodes) + 12,
        [
            ("dot", "mk-ok", "allow"),
            ("dot", "mk-fail", "deny"),
            ("dot", "mk-run", "unknown, never read as deny"),
        ],
    )
    return cv


def build(spec):
    return {
        "nested": nested,
        "layer-stack": layer_stack,
        "loop": loop,
        "fishbone": fishbone,
        "kanban": kanban,
        "venn": venn,
        "timeline": timeline,
        "gantt": gantt,
        "dp-security-matrix": matrix,
    }[spec["type"]](spec)
