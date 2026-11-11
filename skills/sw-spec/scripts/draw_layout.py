"""Deterministic text measurement, canvas bookkeeping, scales and path helpers.

Nothing here reads a browser: widths come from a fixed per-character table, so one
spec always renders the same bytes. Source labels stay data and are escaped on output.
"""

from __future__ import annotations

import math

from draw_common import esc, refs

NARROW = set("iljtfr.,:;'!|()[]/ \"-")
WIDE = set("mwMW@%")


def measure(value, size=15, mono=False, bold=False):
    """Estimated rendered width of one text line in pixels."""
    value = str(value)
    if mono:
        return len(value) * 0.6 * size
    total = 0.0
    for ch in value:
        if ord(ch) >= 0x2E80:
            total += 1.0
        elif ch in WIDE:
            total += 0.86
        elif ch in NARROW:
            total += 0.31
        elif ch.isupper():
            total += 0.68
        elif ch.isdigit():
            total += 0.62
        elif ch in "→↑·—":
            total += 1.0
        else:
            total += 0.55
    return total * size * (1.07 if bold else 1.0)


def micro_width(value, size=12):
    """Width of an uppercase letter-spaced micro label."""
    return measure(str(value).upper(), size, bold=True) + len(str(value)) * 0.08 * size


def ceil4(value):
    return int(math.ceil(value / 4.0) * 4)


def num(value):
    return f"{round(float(value), 2):g}"


def wrap(value, width, size=15, bold=False):
    """Greedy word wrap that never drops text; an over-long word is split by character."""
    lines, current = [], ""
    for word in str(value).split(" "):
        trial = word if not current else current + " " + word
        if measure(trial, size, bold=bold) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
        while measure(current, size, bold=bold) > width and len(current) > 1:
            cut = len(current)
            while cut > 1 and measure(current[:cut], size, bold=bold) > width:
                cut -= 1
            lines.append(current[:cut])
            current = current[cut:]
    lines.append(current)
    return lines


def nice_ticks(low, high, target=5):
    """Return (ticks, low, high) on 1/2/5 x 10^n steps covering [low, high]."""
    if high <= low:
        high = low + 1

    def nice(x, rounded):
        exponent = math.floor(math.log10(x))
        fraction = x / 10**exponent
        if rounded:
            pick = 1 if fraction < 1.5 else 2 if fraction < 3 else 5 if fraction < 7 else 10
        else:
            pick = 1 if fraction <= 1 else 2 if fraction <= 2 else 5 if fraction <= 5 else 10
        return pick * 10**exponent

    span = nice(high - low, False)
    step = nice(span / max(1, target - 1), True)
    start = math.floor(low / step) * step
    stop = math.ceil(high / step) * step
    ticks, value = [], start
    while value <= stop + step * 1e-9:
        ticks.append(round(value, 10))
        value += step
    return ticks, ticks[0], ticks[-1]


def tick_text(value):
    return f"{value:g}"


def simplify(points):
    """Drop repeated and collinear vertices from an orthogonal polyline."""
    out = []
    for p in points:
        if out and abs(out[-1][0] - p[0]) < 1e-6 and abs(out[-1][1] - p[1]) < 1e-6:
            continue
        out.append(p)
    kept = [out[0]] if out else []
    for i in range(1, len(out) - 1):
        a, b, c = out[i - 1], out[i], out[i + 1]
        if (abs(a[0] - b[0]) < 1e-6 and abs(b[0] - c[0]) < 1e-6) or (
            abs(a[1] - b[1]) < 1e-6 and abs(b[1] - c[1]) < 1e-6
        ):
            continue
        kept.append(b)
    if len(out) > 1:
        kept.append(out[-1])
    return kept


def rounded(points, radius=8):
    """SVG path with right-angle corners rounded; returns (d, length)."""
    pts = simplify(points)
    if len(pts) < 2:
        return "", 0.0
    d = [f"M {num(pts[0][0])} {num(pts[0][1])}"]
    length = 0.0
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if i < len(pts) - 1:
            c = pts[i + 1]
            nxt = math.hypot(c[0] - b[0], c[1] - b[1])
            r = min(radius, seg / 2, nxt / 2)
            ux, uy = (b[0] - a[0]) / seg, (b[1] - a[1]) / seg
            vx, vy = (c[0] - b[0]) / nxt, (c[1] - b[1]) / nxt
            p1 = (b[0] - ux * r, b[1] - uy * r)
            p2 = (b[0] + vx * r, b[1] + vy * r)
            d.append(
                f"L {num(p1[0])} {num(p1[1])} Q {num(b[0])} {num(b[1])} {num(p2[0])} {num(p2[1])}"
            )
            length += seg - 2 * r + r * math.pi / 2 * 0.9
        else:
            d.append(f"L {num(b[0])} {num(b[1])}")
            length += seg
    return " ".join(d), length


def squarify(values, x, y, w, h):
    """Squarified treemap rectangles in input order (values must be positive)."""
    total = float(sum(values))
    order = sorted(range(len(values)), key=lambda i: (-values[i], i))
    scale = w * h / total
    rects = {}

    def worst(row, side):
        s = sum(row)
        return max(max(side * side * r / (s * s), s * s / (side * side * r)) for r in row)

    def place(items, rx, ry, rw, rh):
        if not items:
            return
        side = min(rw, rh)
        row = [items[0]]
        rest = items[1:]
        while rest and worst([v for _, v in row + [rest[0]]], side) <= worst(
            [v for _, v in row], side
        ):
            row.append(rest.pop(0))
        area = sum(v for _, v in row)
        thick = area / side if side else 0
        offset = 0.0
        for idx, v in row:
            span = v / thick if thick else 0
            if rw >= rh:
                rects[idx] = (rx, ry + offset, thick, span)
            else:
                rects[idx] = (rx + offset, ry, span, thick)
            offset += span
        if rw >= rh:
            place(rest, rx + thick, ry, rw - thick, rh)
        else:
            place(rest, rx, ry + thick, rw, rh - thick)

    place([(i, values[i] * scale) for i in order], x, y, w, h)
    return [rects[i] for i in range(len(values))]


def glyph(shape, x, y, cls, r=6):
    """Status mark: a shape plus a colour class, never colour alone."""
    if shape == "circle":
        return f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" class="{cls}"/>'
    if shape == "triangle":
        pts = [(x, y - r - 1), (x + r + 1, y + r), (x - r - 1, y + r)]
    elif shape == "diamond":
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    else:
        return (
            f'<rect x="{num(x - r + 1)}" y="{num(y - r + 1)}" width="{num(2 * r - 2)}" '
            f'height="{num(2 * r - 2)}" class="{cls}"/>'
        )
    coords = " ".join(f"{num(px)},{num(py)}" for px, py in pts)
    return f'<polygon points="{coords}" class="{cls}"/>'


def ids_text(node):
    return " · ".join(refs(node))


def tab_width(node):
    text = ids_text(node)
    return measure(text, 12, mono=True) + 16 if text else 0


def overlaps(a, b, pad=0):
    return not (
        a[0] + a[2] + pad <= b[0]
        or b[0] + b[2] + pad <= a[0]
        or a[1] + a[3] + pad <= b[1]
        or b[1] + b[3] + pad <= a[1]
    )


class Placer:
    """Greedy label placement: the first candidate that overlaps nothing placed wins."""

    def __init__(self):
        self.rects = []

    def reserve(self, rect):
        self.rects.append(rect)

    def place(self, w, h, anchors):
        for x, y in anchors:
            rect = (x, y, w, h)
            if not any(overlaps(rect, other, 2) for other in self.rects):
                self.rects.append(rect)
                return rect
        rect = (anchors[0][0], anchors[0][1], w, h)
        self.rects.append(rect)
        return rect


class Canvas:
    """Ordered SVG layers plus the geometry the tests and the page builder need."""

    LAYERS = ("under", "edges", "tickets", "nodes", "over")

    def __init__(self, margin=32):
        self.margin = margin
        self.layers = {name: [] for name in self.LAYERS}
        self.boxes = {}
        self.node_rects = []
        self.ticket_rects = []
        self.bounds = [1e9, 1e9, -1e9, -1e9]
        self.flows = []
        self.routes = []

    def grow(self, x0, y0, x1, y1):
        b = self.bounds
        b[0], b[1], b[2], b[3] = min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)

    def add(self, layer, svg):
        self.layers[layer].append(svg)

    def put(self, layer, svg, box=None):
        self.layers[layer].append(svg)
        if box:
            self.grow(box[0], box[1], box[0] + box[2], box[1] + box[3])

    def rect(self, x, y, w, h, cls="box", r=6, layer="nodes", extra=""):
        svg = (
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" '
            f'rx="{num(r)}" class="{cls}"{" " + extra if extra else ""}/>'
        )
        self.put(layer, svg, (x, y, w, h))

    def line(self, x1, y1, x2, y2, cls="rule", layer="under", extra=""):
        svg = (
            f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
            f'class="{cls}"{" " + extra if extra else ""}/>'
        )
        self.put(layer, svg, (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)))

    def circle(self, x, y, r, cls="solid", layer="nodes", extra=""):
        svg = (
            f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" class="{cls}"'
            f"{' ' + extra if extra else ''}/>"
        )
        self.put(layer, svg, (x - r, y - r, 2 * r, 2 * r))

    def poly(self, points, cls="box", layer="nodes", extra=""):
        coords = " ".join(f"{num(px)},{num(py)}" for px, py in points)
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        svg = f'<polygon points="{coords}" class="{cls}"{" " + extra if extra else ""}/>'
        self.put(layer, svg, (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))

    def path(self, d, cls="edge", layer="edges", extra="", box=None):
        self.put(layer, f'<path d="{d}" class="{cls}"{" " + extra if extra else ""}/>', box)

    def text(
        self, x, y, value, cls="", anchor="start", size=15, mono=False, bold=False, layer="nodes"
    ):
        width = (
            micro_width(value, size)
            if "micro" in cls.split()
            else measure(value, size, mono=mono, bold=bold)
        )
        svg = (
            f'<text x="{num(x)}" y="{num(y)}" class="{cls}" text-anchor="{anchor}">'
            f"{esc(value)}</text>"
        )
        left = x if anchor == "start" else x - width / 2 if anchor == "middle" else x - width
        self.put(layer, svg, (left, y - size, width, size * 1.3))

    def tab(self, node, right, top, layer="nodes"):
        """Source-ID tab: a small mono tag straddling the card's top edge."""
        label = ids_text(node)
        if not label:
            return ""
        w = tab_width(node)
        out = (
            f'<rect x="{num(right - w)}" y="{num(top - 10)}" width="{num(w)}" height="20" '
            f'rx="4" class="tab"/>'
            f'<text x="{num(right - w + 8)}" y="{num(top + 4)}" class="ids">{esc(label)}</text>'
        )
        self.grow(right - w, top - 10, right, top + 10)
        return out

    def ttext(self, x, y, value, cls="", anchor="start", size=15, mono=False, bold=False):
        """Text SVG string for a node group; the canvas bounds still grow."""
        width = (
            micro_width(value, size)
            if "micro" in cls.split()
            else measure(value, size, mono=mono, bold=bold)
        )
        left = x if anchor == "start" else x - width / 2 if anchor == "middle" else x - width
        self.grow(left, y - size, left + width, y + size * 0.3)
        return (
            f'<text x="{num(x)}" y="{num(y)}" class="{cls}" text-anchor="{anchor}">'
            f"{esc(value)}</text>"
        )

    def trect(self, x, y, w, h, cls="box", r=0, extra=""):
        self.grow(x, y, x + w, y + h)
        return (
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" '
            f'rx="{num(r)}" class="{cls}"{" " + extra if extra else ""}/>'
        )

    def tline(self, x1, y1, x2, y2, cls="rule", extra=""):
        self.grow(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        return (
            f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
            f'class="{cls}"{" " + extra if extra else ""}/>'
        )

    def tcircle(self, x, y, r, cls="solid", extra=""):
        self.grow(x - r, y - r, x + r, y + r)
        return (
            f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" class="{cls}"'
            f"{' ' + extra if extra else ''}/>"
        )

    def tpath(self, d, cls="edge", points=None, extra=""):
        if points:
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            self.grow(min(xs), min(ys), max(xs), max(ys))
        return f'<path d="{d}" class="{cls}"{" " + extra if extra else ""}/>'

    def tpoly(self, points, cls="box", extra=""):
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        self.grow(min(xs), min(ys), max(xs), max(ys))
        coords = " ".join(f"{num(px)},{num(py)}" for px, py in points)
        return f'<polygon points="{coords}" class="{cls}"{" " + extra if extra else ""}/>'

    def chip(self, node, x, yc, anchor="start"):
        """Inline source-ID tag centred on yc; returns its SVG (empty without IDs)."""
        label = ids_text(node)
        if not label:
            return ""
        w = tab_width(node)
        left = x if anchor == "start" else x - w
        self.grow(left, yc - 9, left + w, yc + 9)
        return (
            f'<rect x="{num(left)}" y="{num(yc - 9)}" width="{num(w)}" height="18" rx="4" '
            f'class="tab"/><text x="{num(left + 8)}" y="{num(yc + 4)}" class="ids">'
            f"{esc(label)}</text>"
        )

    def label(self, node, x, yc, anchor="start", value=None, name=None, halo=False):
        """Direct label: name, optional value, then the ID chip; returns (svg, width)."""
        name = node["label"] if name is None else name
        lw = measure(name, 15, bold=True)
        vtext = None if value is None else str(value)
        vw = measure(vtext, 15, bold=True) if vtext else 0
        cw = tab_width(node)
        total = lw + (8 + vw if vtext else 0) + (8 + cw if cw else 0)
        left = x if anchor == "start" else x - total if anchor == "end" else x - total / 2
        cls = "node-name halo" if halo else "node-name"
        out = f'<text x="{num(left)}" y="{num(yc + 5)}" class="{cls}">{esc(name)}</text>'
        cursor = left + lw
        if vtext:
            out += (
                f'<text x="{num(cursor + 8)}" y="{num(yc + 5)}" class="value">{esc(vtext)}</text>'
            )
            cursor += 8 + vw
        if cw:
            out += self.chip(node, cursor + 8, yc)
        self.grow(left, yc - 10, left + total, yc + 10)
        return out, total

    def node(self, node, content, box=None, prefix="node"):
        ids = esc(" ".join(refs(node)))
        svg = (
            f'<g class="node" id="{prefix}-{node["id"]}" data-node="{node["id"]}" '
            f'data-spec="{ids}" data-spec-ids="{ids}">{content}</g>'
        )
        self.put("nodes", svg)
        if box:
            self.boxes[node["id"]] = tuple(box)
            self.node_rects.append(tuple(box))

    def finish(self, min_width=0):
        """Return (width, height, body, shift) with the drawing starting at the margin."""
        x0, y0, x1, y1 = self.bounds
        if x1 < x0:
            x0 = y0 = 0
            x1 = y1 = 64
        dx, dy = int(round(self.margin - x0)), int(round(self.margin - y0))
        width = int(math.ceil(x1 - x0 + 2 * self.margin))
        height = int(math.ceil(y1 - y0 + 2 * self.margin))
        if width < min_width:
            dx += int((min_width - width) // 2)
            width = int(math.ceil(min_width))
        body = "".join("".join(self.layers[name]) for name in self.LAYERS)
        if dx or dy:
            self.boxes = {k: (v[0] + dx, v[1] + dy, v[2], v[3]) for k, v in self.boxes.items()}
        return width, height, body, (dx, dy)
