"""The eight business-analysis notations: contract, drawing and Mermaid source."""

from __future__ import annotations

import re

from draw_common import ParagraphRequired, label
from draw_flow import FEdge, FNode, draw, layout
from draw_graphs import (
    card_dims,
    class_graph,
    draw_card,
    flow_edges,
)
from draw_layout import Canvas, ceil4, glyph, measure, micro_width, tab_width, wrap

from kitlib.ids import parse_ref

TYPES = (
    "swimlane",
    "flowchart",
    "journey",
    "service-blueprint",
    "story-map",
    "state",
    "sequence",
    "er",
)
MERMAID = {"flowchart", "journey", "state", "sequence", "er"}


def validate(spec):
    if not isinstance(spec, dict) or spec.get("type") not in TYPES:
        raise ValueError("choose one of the eight BA diagram types")
    kind = spec["type"]
    label(spec.get("title"), 96)
    nodes = spec.get("nodes")
    limit = 12 if kind == "story-map" else 6 if kind == "journey" else 9
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= limit:
        raise ValueError(f"split the diagram: expected 1..{limit} nodes")
    actors = spec.get("actors", ["Reader"])
    if not isinstance(actors, list) or not 1 <= len(actors) <= 6 or len(set(actors)) != len(actors):
        raise ValueError("actors must be 1..6 unique names")
    for actor in actors:
        label(actor, 24)
    if len(nodes) < 5 and len(actors) == 1:
        raise ParagraphRequired("write a paragraph: fewer than 5 steps with one actor")
    names = set()
    for node in nodes:
        if not isinstance(node, dict) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]{0,23}", str(node.get("id", ""))
        ):
            raise ValueError("node ids must be short letters, digits or underscores")
        if node["id"] in names:
            raise ValueError("duplicate node id")
        names.add(node["id"])
        label(node.get("label"), 32)
        refs = node.get("spec_ids", [])
        if (
            not isinstance(refs, list)
            or len(refs) > 3
            or any(not isinstance(r, str) or not parse_ref(r) for r in refs)
        ):
            raise ValueError("spec_ids must contain up to three valid spec references")
        if len(" · ".join(refs)) > 36:
            raise ValueError("split spec IDs across nodes: chip exceeds 36 characters")
        if node.get("actor", actors[0]) not in actors:
            raise ValueError("node actor is not declared")
        if "focal" in node and not isinstance(node["focal"], bool):
            raise ValueError("focal must be true or false")
        if kind == "flowchart" and node.get("kind", "step") not in {
            "start",
            "end",
            "step",
            "decision",
            "merge",
        }:
            raise ValueError("unknown flowchart shape")
        if kind == "journey":
            if node.get("feeling") not in {"high", "neutral", "low"}:
                raise ValueError("journey stages need high, neutral or low feeling")
            for key in ("touchpoint", "owner"):
                label(node.get(key), 28)
        if kind == "service-blueprint":
            cells = node.get("cells", {})
            if not isinstance(cells, dict) or set(cells) - {
                "evidence",
                "customer",
                "frontstage",
                "backstage",
                "support",
            }:
                raise ValueError("unknown blueprint layer")
            for value in cells.values():
                label(value, 28)
        if kind == "story-map" and (
            node.get("activity") not in spec.get("activities", [])
            or node.get("slice") not in spec.get("slices", [])
        ):
            raise ValueError("cards need a declared activity and outcome slice")
        if kind == "er":
            fields = node.get("fields", [])
            if not isinstance(fields, list) or len(fields) > 4:
                raise ValueError("entities allow at most four fields")
            for field in fields:
                label(field, 30)
                if not re.fullmatch(r"(?:PK |FK )?[A-Za-z][A-Za-z0-9_]*", field):
                    raise ValueError("fields use identifiers with optional PK or FK marker")
    if sum(n.get("focal") is True for n in nodes) > 2:
        raise ValueError("at most two focal nodes; emphasis loses meaning beyond that")
    if kind == "journey" and sum(n.get("pain", False) is True for n in nodes) > 2:
        raise ValueError("journey allows at most two pain markers")
    if kind == "journey" and any(n.get("pain") and n["feeling"] != "low" for n in nodes):
        raise ValueError("pain markers belong at low feeling")
    if kind == "story-map":
        for key, cap in (("activities", 5), ("slices", 3)):
            values = spec.get(key)
            if (
                not isinstance(values, list)
                or not 1 <= len(values) <= cap
                or len(set(values)) != len(values)
            ):
                raise ValueError(f"{key} must contain unique names within the budget")
            for value in values:
                label(value, 24)
    edges = spec.get("edges", [])
    if not isinstance(edges, list) or len(edges) > 2 * len(nodes):
        raise ValueError("split the diagram: too many transitions")
    if kind in {"journey", "service-blueprint", "story-map"} and edges:
        raise ValueError("this type uses ordered columns, not arrows")
    for edge in edges:
        if (
            not isinstance(edge, dict)
            or edge.get("from") not in names
            or edge.get("to") not in names
        ):
            raise ValueError("edge endpoint is missing")
        label(edge.get("label"), 48)
        if kind == "sequence" and edge.get("kind", "call") not in {"call", "return", "async"}:
            raise ValueError("unknown sequence message kind")
        if kind == "er" and any(
            edge.get(k) not in {"1", "N", "0..1", "1..*"} for k in ("from_card", "to_card")
        ):
            raise ValueError("ER relationships need cardinality at both ends")
    if kind == "flowchart":
        for node in nodes:
            if node.get("kind") == "decision" and sum(e["from"] == node["id"] for e in edges) > 3:
                raise ValueError("decisions allow at most three exits")
    frames = spec.get("frames", [])
    if kind != "sequence" and frames:
        raise ValueError("frames are only for sequence diagrams")
    if not isinstance(frames, list) or len(frames) > 2:
        raise ValueError("split the sequence: at most two frames")
    for frame in frames:
        if frame.get("kind") not in {"alt", "opt", "loop"}:
            raise ValueError("sequence frames use alt, opt or loop")
        label(frame.get("label"), 32)
        if (
            not isinstance(frame.get("start"), int)
            or not isinstance(frame.get("end"), int)
            or not 0 <= frame["start"] <= frame["end"] < len(edges)
        ):
            raise ValueError("frame bounds must be message indexes")
    if kind == "journey" and len(actors) != 1:
        raise ValueError("journey requires one persona")
    for i, frame in enumerate(frames):
        for other in frames[i + 1 :]:
            if not (frame["end"] < other["start"] or other["end"] < frame["start"]):
                raise ValueError("sequence frames must not overlap; split alternatives")
    return spec


def _flow(spec, nodes, edges, lanes=None):
    cv = Canvas()
    plan = layout(nodes, edges, lanes)
    draw(cv, plan, nodes, edges)
    return cv, plan


def _plain_nodes(spec, lane_of=None, lanes=None):
    dims = {n["id"]: card_dims(n) for n in spec["nodes"]}
    width = max(d[0] for d in dims.values())
    out = []
    for n in spec["nodes"]:
        h = max(52, dims[n["id"]][1])

        def render(cv, x, y, w, hh, n=n):
            draw_card(cv, n, x, y, w, hh)

        out.append(FNode(n["id"], width, h, render, lane_of(n) if lane_of else 0))
    return out


def swimlane(spec):
    lanes = spec.get("actors", ["Reader"])
    nodes = _plain_nodes(spec, lambda n: lanes.index(n.get("actor", lanes[0])))
    cv, _ = _flow(spec, nodes, flow_edges(spec), lanes)
    return cv


def _diamond_dims(label):
    lines = wrap(label, 132, 15, True)
    tw = max(measure(line, 15, bold=True) for line in lines)
    w = max(160, ceil4(2 * (tw + 12)))
    h = max(88, ceil4(2 * (18 * len(lines) + 12)))
    return w, h, lines


def _shape_node(n):
    kind = n.get("kind", "step")
    if kind == "decision":
        w, h, lines = _diamond_dims(n["label"])

        def render(cv, x, y, ww, hh, n=n, lines=lines):
            cx, cy = x + ww / 2, y + hh / 2
            shape = cv.tpoly(
                [(cx, y), (x + ww, cy), (cx, y + hh), (x, cy)],
                "box focal" if n.get("focal") is True else "box",
            )
            text = "".join(
                cv.ttext(
                    cx,
                    cy - 9 * (len(lines) - 1) + 18 * k + 5,
                    line,
                    "node-name",
                    "middle",
                    bold=True,
                )
                for k, line in enumerate(lines)
            )
            tab = cv.tab(n, cx + ww / 4 + tab_width(n) / 2, y + hh / 4)
            cv.node(n, shape + text + tab, (x, y, ww, hh))

        return FNode(n["id"], w, h, render, exits="sides")
    if kind == "merge":

        def render(cv, x, y, ww, hh, n=n):
            body = cv.tcircle(x + 9, y + 9, 9, "solid") + cv.ttext(
                x + 26, y + 14, n["label"], "small", size=13
            )
            cv.node(n, body, (x, y, 18, 18))

        return FNode(n["id"], 18, 18, render)
    w, h, _ = card_dims(n, min_w=204)
    h = max(52, h)

    def render(cv, x, y, ww, hh, n=n, kind=kind):
        radius = hh / 2 if kind in {"start", "end"} else 6
        cls = "box focal" if n.get("focal") is True else "box"
        lines = wrap(n["label"], ww - 32, 15, True)
        body = [cv.trect(x, y, ww, hh, cls, radius)]
        for k, line in enumerate(lines):
            body.append(
                cv.ttext(
                    x + ww / 2,
                    y + hh / 2 - 9 * (len(lines) - 1) + 18 * k + 5,
                    line,
                    "node-name",
                    "middle",
                    bold=True,
                )
            )
        body.append(cv.tab(n, x + ww - 12, y))
        cv.node(n, "".join(body), (x, y, ww, hh))

    return FNode(n["id"], w, h, render)


def flowchart(spec):
    nodes = [_shape_node(n) for n in spec["nodes"]]
    cv, _ = _flow(spec, nodes, flow_edges(spec))
    return cv


def state(spec):
    base = card_dims
    dims = {n["id"]: base(n, min_w=188) for n in spec["nodes"]}
    width = max(d[0] for d in dims.values())
    nodes = []
    for n in spec["nodes"]:
        h = max(52, dims[n["id"]][1])

        def render(cv, x, y, w, hh, n=n):
            draw_card(cv, n, x, y, w, hh, cls=None)

        nodes.append(FNode(n["id"], width, h, render))

    def dot(cv, x, y, w, h):
        cv.add("nodes", cv.tcircle(x + 10, y + 10, 8, "solid"))

    def ring(cv, x, y, w, h):
        cv.add(
            "nodes",
            cv.tcircle(x + 12, y + 12, 11, "hollow") + cv.tcircle(x + 12, y + 12, 6, "solid"),
        )

    nodes += [FNode("~start", 20, 20, dot), FNode("~end", 24, 24, ring)]
    edges = flow_edges(spec)
    edges += [FEdge("~start", spec["nodes"][0]["id"]), FEdge(spec["nodes"][-1]["id"], "~end")]
    cv = Canvas()
    plan = layout(nodes, edges)
    draw(cv, plan, nodes, edges)
    return cv


def sequence(spec):
    cv = Canvas()
    nodes, edges = spec["nodes"], spec.get("edges", [])
    dims = {n["id"]: card_dims(n, min_w=164) for n in nodes}
    width = max(d[0] for d in dims.values())
    height = max(d[1] for d in dims.values())
    index = {n["id"]: i for i, n in enumerate(nodes)}
    pitch = width + 28
    for e in edges:
        a, b = index[e["from"]], index[e["to"]]
        if a != b:
            pitch = max(pitch, (measure(e["label"], 13) + 56) / abs(a - b))
    pitch = ceil4(pitch)
    cx = {n["id"]: i * pitch + width / 2 for i, n in enumerate(nodes)}
    row = 72
    first = height + 76
    bottom = first + row * len(edges) + 24
    for n in nodes:
        draw_card(cv, n, cx[n["id"]] - width / 2, 0, width, height)
        cv.line(cx[n["id"]], height, cx[n["id"]], bottom, "lifeline", "under")
    for f in spec.get("frames", []):
        top = first + f["start"] * row - 52
        low = first + (f["end"] + 1) * row - 28
        left, right = -12, cx[nodes[-1]["id"]] + width / 2 + 12
        cv.rect(left, top, right - left, low - top, "frame", 6, "under")
        tag = f"{f['kind'].upper()} · {f['label']}"
        tw = micro_width(tag) + 24
        cv.rect(left, top, tw, 24, "tab", 6, "under")
        cv.text(left + 12, top + 17, tag, "micro", layer="under", size=12)
    for k, e in enumerate(edges):
        y = first + k * row
        a, b = cx[e["from"]], cx[e["to"]]
        kind = e.get("kind", "call")
        cls = "edge dashed" if kind in {"return", "async"} else "edge"
        cls += f" step d{min(k + 1, 8)}"
        marker = "open" if kind == "async" else "arrow"
        if a == b:
            d = f"M {a:g} {y:g} H {a + 48:g} V {y + 28:g} H {a:g}"
            cv.path(d, cls, "edges", f'marker-end="url(#{marker})"', (a, y, 48, 28))
            cv.text(a + 58, y + 18, e["label"], "small", size=13, layer="tickets")
        else:
            cv.path(
                f"M {a:g} {y:g} H {b:g}",
                cls,
                "edges",
                f'marker-end="url(#{marker})"',
                (min(a, b), y, abs(b - a), 1),
            )
            cv.text((a + b) / 2, y - 10, e["label"], "small", "middle", 13, layer="tickets")
        if kind != "return":
            cv.rect(b - 5, y - 6, 10, 30, "act", 2, "tickets")
    return cv


def er(spec):
    return class_graph(spec)


FEELING = {"high": ("mk-ok", 0), "neutral": ("mk-stop", 1), "low": ("mk-fail", 2)}


def _glyph(kind, cls, x, y):
    shape = {"high": "circle", "low": "triangle"}.get(kind, "square")
    return glyph(shape, x, y, cls, 6)


def journey(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    dims = {n["id"]: card_dims(n, min_w=188) for n in nodes}
    cw = max(
        [d[0] for d in dims.values()]
        + [measure(n["touchpoint"], 13) + 32 for n in nodes]
        + [measure(n["owner"], 13) + 32 for n in nodes]
    )
    cw = ceil4(cw)
    hh = max(d[1] for d in dims.values())
    lw, gap = 112, 16
    rows = {"touchpoint": hh + 40, "owner": hh + 84}
    top, band = hh + 112, 120
    levels = {"high": top + 28, "neutral": top + 60, "low": top + 92}
    for name, y in rows.items():
        cv.text(0, y + 5, name, "micro", layer="under", size=12)
    cv.text(0, top + 28, "high", "micro", layer="under", size=12)
    cv.text(0, top + 60, "neutral", "micro", layer="under", size=12)
    cv.text(0, top + 92, "low", "micro", layer="under", size=12)
    for y in levels.values():
        cv.line(lw, y, lw + len(nodes) * (cw + gap) - gap, y, "grid", "under")
    pts = []
    for i, n in enumerate(nodes):
        x = lw + i * (cw + gap)
        out = []
        draw_card_group = []
        draw_card(cv, n, x, 0, cw, hh)
        for name, y in rows.items():
            draw_card_group.append(cv.ttext(x + cw / 2, y + 5, n[name], "small", "middle", 13))
        cls, _ = FEELING[n["feeling"]]
        py = levels[n["feeling"]]
        pts.append((x + cw / 2, py, n))
        out.append(_glyph(n["feeling"], cls, x + cw / 2, py))
        cv.grow(x + cw / 2 - 8, py - 8, x + cw / 2 + 8, py + 8)
        if n.get("pain"):
            out.append(cv.ttext(x + cw / 2 + 14, py + 5, "Pain", "value halo", bold=True))
        cv.add("nodes", "".join(draw_card_group) + "".join(out))
    d = "M " + " L ".join(f"{px:g} {py:g}" for px, py, _ in pts)
    cv.path(d, "curve", "edges", box=(lw, top, cw * len(nodes), band))
    for (ax, ay, _), (bx, by, nb) in zip(pts, pts[1:], strict=False):
        cv.flows.append(
            (f"M {ax:g} {ay:g} L {bx:g} {by:g}", ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5, nb["id"])
        )
    return cv


BLUEPRINT = ("evidence", "customer", "frontstage", "backstage", "support")


def service_blueprint(spec):
    cv = Canvas()
    nodes = spec["nodes"]
    dims = {n["id"]: card_dims(n, min_w=188) for n in nodes}
    cw = ceil4(
        max(
            [d[0] for d in dims.values()]
            + [measure(v, 13) + 32 for n in nodes for v in n.get("cells", {}).values()]
        )
    )
    hh = max(d[1] for d in dims.values())
    lw, gap, rh = 112, 12, 52
    top = hh + 24
    total_w = lw + len(nodes) * (cw + gap) - gap
    for r, name in enumerate(BLUEPRINT):
        y = top + r * rh
        internal = name in {"backstage", "support"}
        cv.rect(0, y, total_w, rh, "lane" if internal else "frame", 4, "under")
        cv.text(12, y + rh / 2 + 4, name, "micro", layer="under", size=12)
        if name == "backstage":
            cv.line(0, y, total_w, y, "visibility", "over")
            pw = micro_width("line of visibility") + 20
            cv.rect(lw - pw - 8, y - 11, pw, 22, "ticket", 11, "over")
            cv.text(lw - pw + 2, y + 4, "line of visibility", "micro", layer="over", size=12)
    for i, n in enumerate(nodes):
        x = lw + i * (cw + gap)
        draw_card(cv, n, x, 0, cw, hh)
        out = []
        for r, name in enumerate(BLUEPRINT):
            value = n.get("cells", {}).get(name, "n/a")
            cls = "small" if value != "n/a" else "small"
            out.append(cv.ttext(x + cw / 2, top + r * rh + rh / 2 + 5, value, cls, "middle", 13))
        cv.add("nodes", "".join(out))
    return cv


def story_map(spec):
    cv = Canvas()
    nodes, acts, slices = spec["nodes"], spec["activities"], spec["slices"]
    dims = {n["id"]: card_dims(n, min_w=188) for n in nodes}
    cw = max(d[0] for d in dims.values()) + 24
    lw = ceil4(max(micro_width(s) for s in slices) + 24)
    stacks = {}
    for n in nodes:
        stacks.setdefault((n["activity"], n["slice"]), []).append(n)
    heights = []
    for s in slices:
        cells = [sum(dims[n["id"]][1] + 14 for n in stacks.get((a, s), [])) for a in acts]
        heights.append(max(max(cells), 72) + 28)
    for i, a in enumerate(acts):
        cv.text(lw + i * cw + cw / 2, 0, a, "node-name", "middle", bold=True, layer="under")
    y = 24
    for si, s in enumerate(slices):
        cv.line(0, y, lw + len(acts) * cw, y, "visibility", "under")
        cv.text(0, y + 20, s, "micro", layer="under", size=12)
        for ai, a in enumerate(acts):
            cy = y + 24
            for n in stacks.get((a, s), []):
                h = dims[n["id"]][1]
                draw_card(cv, n, lw + ai * cw + 12, cy, cw - 24, h)
                cy += h + 14
        y += heights[si]
    cv.line(0, y, lw + len(acts) * cw, y, "visibility", "under")
    return cv


BUILDERS = {
    "swimlane": swimlane,
    "flowchart": flowchart,
    "journey": journey,
    "service-blueprint": service_blueprint,
    "story-map": story_map,
    "state": state,
    "sequence": sequence,
    "er": er,
}


def build(spec):
    return BUILDERS[spec["type"]](spec)


def mermaid(spec):
    kind = spec["type"]
    if kind not in MERMAID:
        return None
    nodes = spec["nodes"]
    aliases = {n["id"]: f"n{i}" for i, n in enumerate(nodes)}

    def quoted(value):
        return "".join(c if c.isalnum() or c == " " else f"#{ord(c)};" for c in value)

    labels = {
        n["id"]: quoted(
            n["label"] + (" (" + ", ".join(n["spec_ids"]) + ")" if n.get("spec_ids") else "")
        )
        for n in nodes
    }
    lines = [
        {
            "state": "stateDiagram-v2",
            "flowchart": "flowchart TD",
            "sequence": "sequenceDiagram",
            "er": "erDiagram",
            "journey": "journey",
        }[kind]
    ]
    for node in nodes:
        key, name = aliases[node["id"]], labels[node["id"]]
        if kind == "state":
            lines.append(f'    state "{name}" as {key}')
        elif kind == "sequence":
            lines.append(f"    participant {key} as {name}")
        elif kind == "er":
            lines.append(f'    {key}["{name}"] {{')
            for field in node.get("fields", []):
                parts = field.split()
                lines.append(
                    f"        string {parts[-1]}" + (f" {parts[0]}" if len(parts) > 1 else "")
                )
            lines.append("    }")
        elif kind == "flowchart":
            shape = node.get("kind", "step")
            left, right = {
                "decision": ('{"', '"}'),
                "start": ('(["', '"])'),
                "end": ('(["', '"])'),
                "merge": ('(("', '"))'),
            }.get(shape, ('["', '"]'))
            lines.append(f"    {key}{left}{name}{right}")
        else:
            lines.extend(
                [
                    f"    section {name}",
                    f"    {name}: { {'high': 5, 'neutral': 3, 'low': 1}[node['feeling']] }: Reader",
                ]
            )
    if kind == "state":
        lines.append(f"    [*] --> {aliases[nodes[0]['id']]}")
    cards = {"1": "||", "N": "o{", "0..1": "o|", "1..*": "|{"}
    for i, edge in enumerate(spec.get("edges", [])):
        a, b, name = aliases[edge["from"]], aliases[edge["to"]], quoted(edge["label"])
        if kind == "sequence":
            for frame in spec.get("frames", []):
                if frame["start"] == i:
                    lines.append(f"    {frame['kind']} {quoted(frame['label'])}")
            arrow = {"call": "->>", "return": "-->>", "async": "--)"}[edge.get("kind", "call")]
            lines.append(f"    {a}{arrow}{b}: {name}")
            for frame in reversed(spec.get("frames", [])):
                if frame["end"] == i:
                    lines.append("    end")
        elif kind == "er":
            left = {"1": "||", "N": "}o", "0..1": "|o", "1..*": "}|"}[edge["from_card"]]
            lines.append(f'    {a} {left}--{cards[edge["to_card"]]} {b} : "{name}"')
        elif kind == "state":
            lines.append(f"    {a} --> {b}: {name}")
        else:
            lines.append(f'    {a} -->|"{name}"| {b}')
    if kind == "state":
        lines.append(f"    {aliases[nodes[-1]['id']]} --> [*]")
    return "\n".join(lines) + "\n"
