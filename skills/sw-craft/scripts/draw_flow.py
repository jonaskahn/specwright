"""Layered top-to-bottom layout and orthogonal routing for connector diagrams.

Layers come from longest paths after reversing back edges; long edges pass through
dummy slots so they never cross a card; every connector leaves and enters on its own
port and bends only at right angles. Labels are masked tickets placed on a straight
run where they overlap no card, ticket or foreign connector.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from draw_common import esc
from draw_layout import measure, micro_width, num, overlaps, rounded, wrap

GAPX = 48
PAD = 24
LANE_GAP = 16
HEAD = 44
MIN_GAP = 100
TRACK = 12


@dataclass
class FNode:
    id: str
    w: float
    h: float
    draw: Callable | None = None
    lane: int = 0
    exits: str = "bottom"


@dataclass
class FEdge:
    src: str
    dst: str
    label: str = ""
    end: str | None = "arrow"
    start: str | None = None
    dashed: bool = False
    deco: Callable | None = None
    css: str = ""


@dataclass
class Routed:
    points: list
    back: bool
    ticket: tuple | None = None
    lines: list = field(default_factory=list)
    gaps: list = field(default_factory=list)
    self_loop: bool = False


@dataclass
class Plan:
    place: dict
    routes: list
    lanes: list
    top: float
    bottom: float
    left: float
    right: float


def assign_layers(ids, pairs):
    adj = {i: [] for i in ids}
    indeg = dict.fromkeys(ids, 0)
    for a, b in pairs:
        if a != b:
            adj[a].append(b)
            indeg[b] += 1
    state, back = {}, set()

    def visit(u):
        state[u] = 1
        for v in adj[u]:
            if state.get(v, 0) == 0:
                visit(v)
            elif state[v] == 1:
                back.add((u, v))
        state[u] = 2

    for start in sorted(ids, key=lambda i: (indeg[i] > 0, ids.index(i))):
        if state.get(start, 0) == 0:
            visit(start)
    forward = [(a, b) if (a, b) not in back else (b, a) for a, b in pairs if a != b]
    layer = dict.fromkeys(ids, 0)
    for _ in range(len(ids) + 1):
        changed = False
        for a, b in forward:
            if layer[b] < layer[a] + 1:
                layer[b] = layer[a] + 1
                changed = True
        if not changed:
            break
    return layer, back


def _segments(points):
    return [(points[i], points[i + 1]) for i in range(len(points) - 1)]


def _hits(rect, seg, pad=3):
    (ax, ay), (bx, by) = seg
    x0, x1 = min(ax, bx) - pad, max(ax, bx) + pad
    y0, y1 = min(ay, by) - pad, max(ay, by) + pad
    return not (x1 < rect[0] or x0 > rect[0] + rect[2] or y1 < rect[1] or y0 > rect[1] + rect[3])


def ticket_lines(label):
    lines = wrap(label, 220, 13)
    w = max(measure(line, 13) for line in lines) + 20
    h = max(22, 14 * len(lines) + 8)
    return lines, w, h


def layout(nodes, edges, lane_names=None, fixed_x=None, x0=0, y0=0):
    by = {n.id: n for n in nodes}
    ids = [n.id for n in nodes]
    pairs = [(e.src, e.dst) for e in edges]
    layer, back = assign_layers(ids, pairs)
    lane_of = {n.id: n.lane for n in nodes}
    lanes_n = max(1, len(lane_names or [])) if lane_names else max(lane_of.values(), default=0) + 1
    has_lanes = bool(lane_names)

    chains = []
    dummy_layer, dummy_lane = {}, {}
    for i, e in enumerate(edges):
        if e.src == e.dst:
            chains.append(None)
            continue
        lo, hi = (e.src, e.dst) if (e.src, e.dst) not in back else (e.dst, e.src)
        chain = [lo]
        for lv in range(layer[lo] + 1, layer[hi]):
            d = f"~{i}.{lv}"
            dummy_layer[d], dummy_lane[d] = lv, lane_of[lo]
            chain.append(d)
        chain.append(hi)
        chains.append(chain)

    def lay(i):
        return layer[i] if i in layer else dummy_layer[i]

    def lane(i):
        return lane_of[i] if i in lane_of else dummy_lane[i]

    def width(i):
        return by[i].w if i in by else 24

    def height(i):
        return by[i].h if i in by else 0

    allids = ids + list(dummy_layer)
    maxlayer = max((lay(i) for i in allids), default=0)
    cells = {}
    for i in allids:
        cells.setdefault((lay(i), lane(i)), []).append(i)
    up, down = {i: [] for i in allids}, {i: [] for i in allids}
    for chain in chains:
        for u, v in zip(chain or [], (chain or [])[1:], strict=False):
            down[u].append(v)
            up[v].append(u)

    def rank(i):
        key = (lane(i), cells[(lay(i), lane(i))].index(i))
        return key[0] * 1000 + key[1]

    if fixed_x is None:
        for sweep in range(4):
            order = range(1, maxlayer + 1) if sweep % 2 == 0 else range(maxlayer - 1, -1, -1)
            for lv in order:
                for (cl, ln), members in list(cells.items()):
                    if cl != lv:
                        continue
                    neighbours = up if sweep % 2 == 0 else down

                    def bary(i, neighbours=neighbours):
                        ns = neighbours[i]
                        return sum(rank(n) for n in ns) / len(ns) if ns else rank(i)

                    cells[(cl, ln)] = sorted(members, key=bary)

    # --- x coordinates
    place_x = {}
    lane_x, lane_w = [], []
    cursor = x0
    for k in range(lanes_n):
        inner = 0
        for lv in range(maxlayer + 1):
            members = cells.get((lv, k), [])
            if members:
                inner = max(inner, sum(width(i) for i in members) + GAPX * (len(members) - 1))
        pad = PAD if has_lanes else 0
        heading = micro_width(lane_names[k]) + 32 if has_lanes else 0
        lane_x.append(cursor)
        lane_w.append(max(inner + 2 * pad, heading, 160))
        cursor += lane_w[-1] + (LANE_GAP if has_lanes else 0)
    for (_lv, k), members in cells.items():
        span = sum(width(i) for i in members) + GAPX * (len(members) - 1)
        left = lane_x[k] + (lane_w[k] - span) / 2
        for i in members:
            place_x[i] = left
            left += width(i) + GAPX
    if fixed_x is not None:
        for i in allids:
            place_x[i] = fixed_x[i] - width(i) / 2
    cx = {i: place_x[i] + width(i) / 2 for i in allids}

    # --- ports
    hops = []  # (chain index, u, v)
    for ci, chain in enumerate(chains):
        for u, v in zip(chain or [], (chain or [])[1:], strict=False):
            hops.append((ci, u, v))
    out_of, in_of = {}, {}
    for h in hops:
        out_of.setdefault(h[1], []).append(h)
        in_of.setdefault(h[2], []).append(h)

    def spread(items, i, key):
        ordered = sorted(items, key=lambda h: (cx[key(h)], h[0]))
        n = len(ordered)
        step = width(i) / (n + 1)
        if i not in by:
            return {h: cx[i] for h in ordered}
        if step < TRACK:
            return {h: cx[i] + (k - (n - 1) / 2) * TRACK for k, h in enumerate(ordered)}
        return {h: place_x[i] + step * (k + 1) for k, h in enumerate(ordered)}

    out_x, in_x, side_exit = {}, {}, {}
    for i, items in in_of.items():
        in_x.update(spread(items, i, lambda h: h[1]))
    for i, items in out_of.items():
        if i in by and by[i].exits == "sides" and len(items) > 1:
            ordered = sorted(items, key=lambda h: (cx[h[2]], h[0]))
            n = len(ordered)
            targets_same = len({round(cx[h[2]]) for h in ordered}) == 1
            names = (
                ["bottom", "right"]
                if n == 2 and targets_same
                else ["left", "right"]
                if n == 2
                else ["left"] + ["bottom"] * (n - 2) + ["right"]
            )
            left_edge, right_edge = place_x[i], place_x[i] + width(i)
            for h, name in zip(ordered, names, strict=True):
                if name == "bottom":
                    out_x[h] = cx[i]
                    continue
                side_exit[h] = name
                if name == "left":
                    out_x[h] = in_x[h] if in_x[h] <= left_edge - 16 else left_edge - 20
                else:
                    out_x[h] = in_x[h] if in_x[h] >= right_edge + 16 else right_edge + 20
        else:
            out_x.update(spread(items, i, lambda h: h[2]))

    # --- gap rows and tracks
    gap_hops = {lv: [] for lv in range(maxlayer)}
    for h in hops:
        gap_hops[lay(h[1])].append(h)
    tracks = {}
    for lv, items in gap_hops.items():
        moving = [h for h in items if abs(out_x[h] - in_x[h]) > 0.5]
        right_going = sorted((h for h in moving if in_x[h] > out_x[h]), key=lambda h: -out_x[h])
        left_going = sorted((h for h in moving if in_x[h] < out_x[h]), key=lambda h: out_x[h])
        tracks[lv] = right_going + left_going

    extra = dict.fromkeys(range(maxlayer + 1), 0)
    for _attempt in range(10):
        row_h = {}
        for lv in range(maxlayer + 1):
            hs = [height(i) for i in allids if lay(i) == lv]
            row_h[lv] = max(hs) if hs else 24
            if row_h[lv] == 0:
                row_h[lv] = 24
        row_y = {}
        y = y0 + (HEAD if has_lanes else 0) + 14
        gap = {}
        for lv in range(maxlayer + 1):
            row_y[lv] = y
            n = len(tracks.get(lv, []))
            gap[lv] = MIN_GAP + TRACK * max(0, n - 1) + extra[lv]
            y += row_h[lv] + gap[lv]
        bottom = y - gap[maxlayer] + 20
        place = {}
        for i in ids:
            n = by[i]
            place[i] = (place_x[i], row_y[lay(i)] + (row_h[lay(i)] - n.h) / 2, n.w, n.h)

        def top_of(i, place=place, row_y=row_y):
            return place[i][1] if i in place else row_y[lay(i)]

        def bottom_of(i, place=place, row_y=row_y, row_h=row_h):
            return place[i][1] + place[i][3] if i in place else row_y[lay(i)] + row_h[lay(i)]

        routes = []
        for ci, e in enumerate(edges):
            chain = chains[ci]
            if chain is None:
                n = place[e.src]
                x, ytop, w, h = n
                pts = [
                    (x + w, ytop + h * 0.3),
                    (x + w + 28, ytop + h * 0.3),
                    (x + w + 28, ytop + h * 0.7),
                    (x + w, ytop + h * 0.7),
                ]
                routes.append(Routed(pts, False, self_loop=True))
                continue
            pts, gaps_used = [], []
            for u, v in zip(chain, chain[1:], strict=False):
                h = next(k for k in hops if k[0] == ci and k[1] == u and k[2] == v)
                lv = lay(u)
                xs, xe = out_x[h], in_x[h]
                ys, ye = bottom_of(u), top_of(v)
                if h in side_exit:
                    cy = place[u][1] + place[u][3] / 2
                    sx = place[u][0] if side_exit[h] == "left" else place[u][0] + place[u][2]
                    pts += [(sx, cy), (xs, cy)]
                else:
                    pts.append((xs, ys))
                gaps_used.append(lv)
                if abs(xs - xe) > 0.5:
                    k = tracks[lv].index(h)
                    n = len(tracks[lv])
                    gap_top = row_y[lv] + row_h[lv]
                    base = gap_top + (gap[lv] - TRACK * (n - 1)) / 2
                    yt = base + TRACK * k
                    pts += [(xs, ys), (xs, yt), (xe, yt), (xe, ye)]
                else:
                    pts.append((xe, ye))
            routes.append(Routed(pts, (e.src, e.dst) in back, gaps=gaps_used))

        # --- tickets
        node_rects = [place[i] for i in ids]
        placed = []
        failures = set()
        for ci, e in enumerate(edges):
            r = routes[ci]
            if not e.label:
                continue
            lines, w, h = ticket_lines(e.label)
            r.lines = lines
            segs = _segments(r.points) if not r.self_loop else _segments(r.points)
            others = [s for cj, o in enumerate(routes) if cj != ci for s in _segments(o.points)]
            if r.self_loop:
                px, py = r.points[1][0] + 10, (r.points[1][1] + r.points[2][1]) / 2
                r.ticket = (px, py - h / 2, w, h)
                placed.append(r.ticket)
                continue
            cands = []
            for si, ((ax, ay), (bx, by_)) in enumerate(segs):
                if abs(ay - by_) < 0.5 and abs(ax - bx) >= w + 40:
                    cands.append((si, (ax + bx) / 2, ay))
            for si, ((ax, ay), (bx, by_)) in enumerate(segs):
                if abs(ax - bx) < 0.5 and abs(by_ - ay) >= h + 16:
                    lo_y, hi_y = min(ay, by_) + 8 + h / 2, max(ay, by_) - 8 - h / 2
                    mid = (lo_y + hi_y) / 2
                    cys = [mid]
                    step = 4
                    while mid - step >= lo_y - 0.01 or mid + step <= hi_y + 0.01:
                        if mid - step >= lo_y - 0.01:
                            cys.append(mid - step)
                        if mid + step <= hi_y + 0.01:
                            cys.append(mid + step)
                        step += 4
                    cands += [(si, ax, yy) for yy in cys]
            chosen = None
            for si, xc, yc in cands:
                rect = (xc - w / 2, yc - h / 2, w, h)
                if any(overlaps(rect, n, 4) for n in node_rects):
                    continue
                if any(overlaps(rect, t, 6) for t in placed):
                    continue
                if any(_hits(rect, s) for s in others):
                    continue
                if any(_hits(rect, s, 1) for k, s in enumerate(segs) if k != si):
                    continue
                chosen = rect
                break
            if chosen is None:
                failures.add(ci)
                if cands:
                    si, xc, yc = cands[0]
                    chosen = (xc - w / 2, yc - h / 2, w, h)
                else:
                    chosen = (r.points[0][0] - w / 2, r.points[0][1] + 8, w, h)
            r.ticket = chosen
            placed.append(chosen)
        if not failures:
            break
        for ci in failures:
            for lv in set(routes[ci].gaps):
                extra[lv] += 24
    lanes = [
        (lane_x[k], lane_w[k], (lane_names or [""])[k] if has_lanes else "") for k in range(lanes_n)
    ]
    right = max([lane_x[-1] + lane_w[-1]] + [p[0] + p[2] for p in place.values()])
    return Plan(place, routes, lanes if has_lanes else [], y0, bottom, x0, right)


def draw(
    cv,
    plan,
    nodes,
    edges,
    dx=0.0,
    dy=0.0,
    visible=None,
    edge_visible=None,
    ghosts=True,
    step_class=False,
):
    """Draw lanes, connectors, tickets and cards of a plan into a canvas."""
    for x, w, name in plan.lanes:
        cv.rect(x + dx, plan.top + dy, w, plan.bottom - plan.top, "lane", 8, "under")
        cv.text(x + dx + 16, plan.top + dy + 26, name, "micro", layer="under", size=12)
    flow_index = 0
    for ci, e in enumerate(edges):
        if edge_visible is not None and not edge_visible(ci, e):
            continue
        r = plan.routes[ci]
        pts = [(px + dx, py + dy) for px, py in r.points]
        d, length = rounded(pts, 8)
        classes = (
            "edge" + (" dashed" if e.dashed or r.back else "") + (" " + e.css if e.css else "")
        )
        if step_class:
            classes += f" step d{min(flow_index + 1, 8)}"
        attrs = []
        start, end = (e.end, e.start) if r.back else (e.start, e.end)
        if start:
            attrs.append(f'marker-start="url(#{start})"')
        if end:
            attrs.append(f'marker-end="url(#{end})"')
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        cv.path(
            d,
            classes,
            "edges",
            " ".join(attrs),
            (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
        )
        if e.deco:
            e.deco(cv, pts, r.back)
        if r.ticket:
            tx, ty, tw, th = r.ticket
            tx, ty = tx + dx, ty + dy
            radius = th / 2 if len(r.lines) == 1 else 8
            cv.put(
                "tickets",
                f'<rect x="{num(tx)}" y="{num(ty)}" width="{num(tw)}" height="{num(th)}" '
                f'rx="{num(radius)}" class="ticket"/>',
                (tx, ty, tw, th),
            )
            cv.ticket_rects.append((tx, ty, tw, th))
            for li, line in enumerate(r.lines):
                cv.put(
                    "tickets",
                    f'<text x="{num(tx + tw / 2)}" y="{num(ty + 4 + 14 * (li + 1) - 2)}" '
                    f'class="small" text-anchor="middle">{esc(line)}</text>',
                )
        cv.flows.append((d, length, e.dst))
        cv.routes.append(pts)
        flow_index += 1
    for n in nodes:
        x, y, w, h = plan.place[n.id]
        if visible is not None and n.id not in visible:
            if ghosts:
                cv.rect(x + dx, y + dy, w, h, "ghost", 6, "under")
            continue
        n.draw(cv, x + dx, y + dy, w, h)
