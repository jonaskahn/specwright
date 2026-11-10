#!/usr/bin/env python3
"""Render a bounded JSON diagram without fetching resources.

Exit codes: 0 rendered, 2 invalid input or I/O failure, 3 write a paragraph instead.
"""

import html
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from check_offline import check_text  # noqa: E402

from kitlib.ids import parse_ref  # noqa: E402

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
ASSETS = _here.parent / "assets"


class ParagraphRequired(ValueError):
    pass


def label(value, maximum=48):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"text must contain 1..{maximum} characters")
    if "<" in value or any(ord(c) < 32 for c in value) or check_text(value):
        raise ValueError("labels must be plain offline text without markup or controls")
    return value


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


def esc(value):
    return html.escape(str(value), quote=True)


def text(x, y, value, cls=""):
    return f'<text x="{x}" y="{y}" class="{cls}">{esc(value)}</text>'


def rect(x, y, w, h, cls="box", radius=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" class="{cls}"/>'


def line(x, y, xx, yy, cls="rule"):
    return f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" class="{cls}"/>'


def slice_height(spec):
    counts = {}
    for node in spec["nodes"]:
        key = (node["activity"], node["slice"])
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values(), default=1) * 112 + 64


def layout(spec):
    kind, nodes = spec["type"], spec["nodes"]
    boxes = {}
    if kind == "story-map":
        counts = {}
        for node in nodes:
            col = spec["activities"].index(node["activity"])
            row = spec["slices"].index(node["slice"])
            slot = counts.get((col, row), 0)
            counts[col, row] = slot + 1
            boxes[node["id"]] = (
                200 + col * 360,
                140 + row * slice_height(spec) + slot * 112,
                320,
                96,
            )
    else:
        for i, node in enumerate(nodes):
            x, y, w, h = 200, 80 + i * 152, 320, 96
            if kind == "swimlane":
                y = (
                    100
                    + spec.get("actors", ["Reader"]).index(
                        node.get("actor", spec.get("actors", ["Reader"])[0])
                    )
                    * 176
                )
                x = 200 + i * 368
            if kind in {"journey", "service-blueprint", "sequence"}:
                x, y = 200 + i * 368, 80
            if kind == "er":
                h, y = 224, 80 + i * 280
            boxes[node["id"]] = (x, y, w, h)
    return boxes


def node_svg(node, box, kind, focal=False):
    x, y, w, h = box
    refs = node.get("spec_ids", [])
    out = [
        f'<g class="node" id="node-{esc(node["id"])}" '
        f'data-node="{esc(node["id"])}" data-spec="{esc(" ".join(refs))}" '
        f'data-spec-ids="{esc(" ".join(refs))}" data-box="{x},{y},{w},{h}">'
    ]
    shape = node.get("kind", "step")
    if kind == "flowchart" and shape == "decision":
        out.append(
            f'<polygon points="{x + w // 2},{y - 24} {x + w + 40},{y + h // 2} '
            f'{x + w // 2},{y + h + 24} {x - 40},{y + h // 2}" class="box"/>'
        )
    elif kind == "flowchart" and shape == "merge":
        out.append(f'<circle cx="{x + 16}" cy="{y + 24}" r="8" class="solid"/>')
    else:
        out.append(
            rect(
                x,
                y,
                w,
                h,
                "box focal" if focal else "box",
                24 if kind == "state" else 40 if shape in {"start", "end"} else 8,
            )
        )
    out.append(text(x + 24, y + 32, node["label"]))
    if refs:
        out.append(rect(x + 16, y + h - 44, w - 32, 32, "chip", 4))
        out.append(text(x + 24, y + h - 22, " · ".join(refs), "ids"))
    if kind == "er":
        out.append(line(x, y + 48, x + w, y + 48))
        for i, field in enumerate(node.get("fields", [])):
            out.append(text(x + 24, y + 76 + i * 28, field, "ids"))
    out.append("</g>")
    return "".join(out)


def render_svg(spec):
    kind, nodes = spec["type"], spec["nodes"]
    boxes = layout(spec)
    width = max(b[0] + b[2] for b in boxes.values()) + 520 + len(spec.get("edges", [])) * 24
    height = max(b[1] + b[3] for b in boxes.values()) + 100
    out = []
    if kind == "swimlane":
        height = 100 + len(spec.get("actors", ["Reader"])) * 176
        for i, actor in enumerate(spec.get("actors", ["Reader"])):
            y = 80 + i * 176
            out.extend(
                [
                    rect(8, y, width - 16, 176, "tint" if i % 2 else "paper"),
                    text(24, y + 48, actor),
                    line(8, y, width - 8, y),
                ]
            )
    if kind in {"journey", "service-blueprint"}:
        rows = (
            ["actions", "touchpoints", "owner", "feeling"]
            if kind == "journey"
            else ["evidence", "customer", "frontstage", "backstage", "support"]
        )
        height = 240 + 112 * len(rows)
        points = []
        for row, name in enumerate(rows):
            y = 208 + row * 112
            out.extend(
                [
                    rect(
                        8,
                        y,
                        width - 16,
                        112,
                        "tint" if name in {"backstage", "support"} else "paper",
                    ),
                    text(24, y + 40, name),
                    line(8, y, width - 8, y, "visibility" if name == "backstage" else "rule"),
                ]
            )
            for node in nodes:
                x = boxes[node["id"]][0] + 24
                if kind == "service-blueprint":
                    value = node.get("cells", {}).get(name, "n/a")
                else:
                    value = {
                        "actions": node["label"],
                        "touchpoints": node["touchpoint"],
                        "owner": node["owner"],
                        "feeling": node["feeling"],
                    }[name]
                if (
                    kind == "service-blueprint"
                    and name == "frontstage"
                    and node["id"] == next((n["id"] for n in nodes if n.get("spec_ids")), None)
                ):
                    out.append(rect(x - 8, y + 8, 304, 88, "box focal", 8))
                out.append(text(x, y + 40, value))
                if name == "feeling":
                    py = y + {"high": 56, "neutral": 72, "low": 88}[node["feeling"]]
                    points.append(f"{x + 80},{py}")
                    if node.get("pain"):
                        out.append(text(x + 104, py, "Pain", "halo"))
        if points:
            out.append(f'<polyline points="{" ".join(points)}" class="curve"/>')
    if kind == "story-map":
        height = 200 + len(spec["slices"]) * slice_height(spec)
        for i, activity in enumerate(spec["activities"]):
            out.append(text(200 + i * 360, 64, activity))
        for i, outcome in enumerate(spec["slices"]):
            out.extend(
                [
                    text(16, 120 + i * slice_height(spec), outcome),
                    line(
                        8,
                        112 + i * slice_height(spec),
                        width - 8,
                        112 + i * slice_height(spec),
                        "visibility",
                    ),
                ]
            )
    if kind == "sequence":
        height = 280 + len(spec.get("edges", [])) * 88
        for box in boxes.values():
            x, y, w, h = box
            out.append(line(x + w // 2, y + h, x + w // 2, height - 40, "lifeline"))
        for frame in spec.get("frames", []):
            y = 192 + frame["start"] * 88
            out.extend(
                [
                    rect(160, y, width - 200, (frame["end"] - frame["start"] + 1) * 88, "frame"),
                    text(168, y + 20, frame["kind"] + " " + frame["label"], "halo"),
                ]
            )
    for i, edge in enumerate(spec.get("edges", [])):
        a, b = boxes[edge["from"]], boxes[edge["to"]]
        x, y, w, h = a
        xx, yy, ww, hh = b
        cls = "edge dashed" if edge.get("kind") in {"return", "async"} else "edge"
        marker = "open" if edge.get("kind") == "async" else "arrow"
        if kind == "sequence":
            sy = 240 + i * 88
            sx, ex = x + w // 2, xx + ww // 2
            d = f"M {sx} {sy} H {ex}" if sx != ex else f"M {sx} {sy} h 80 v 32 h -80"
            lx, ly = min(sx, ex) + 16, sy - 12
            out.append(rect(ex - 8, sy - 8, 16, 48, "chip"))
        elif kind == "swimlane":
            sx, sy, ex, ey = x + w, y + h // 2, xx, yy + hh // 2
            bend = sx + 24 + i * 8
            d = f"M {sx} {sy} H {bend} V {ey} H {ex}"
            lx, ly = sx + 8, sy - 12
        else:
            # Each connection gets its own outside gutter so boxes never hide a transition.
            gutter = 600 + i * 24
            sy, ey = y + h // 2, yy + hh // 2
            if edge["from"] == edge["to"]:
                d = f"M {x + w - 48} {y} V {y - 40} H {x + w + 48} V {y + 24} H {x + w}"
                lx, ly = x + 40, y - 48
            else:
                d = f"M {x + w} {sy} H {gutter} V {ey} H {xx + ww}"
                lx, ly = gutter + 8, (sy + ey) // 2
        out.append(f'<path d="{d}" class="{cls}" marker-end="url(#{marker})"/>')
        caption = edge["label"]
        if kind == "er":
            caption = edge["from_card"] + " : " + caption + " : " + edge["to_card"]
            out.extend(
                [
                    text(x + w + 8, y + 32, edge["from_card"], "halo"),
                    text(xx + ww + 8, yy + hh - 8, edge["to_card"], "halo"),
                ]
            )
        out.append(text(lx, ly, caption, "halo small"))
    focal_ids = [n["id"] for n in nodes if n.get("spec_ids")][:2]
    for node in nodes:
        out.append(
            node_svg(
                node,
                boxes[node["id"]],
                kind,
                node["id"] in focal_ids and kind != "service-blueprint",
            )
        )
    if kind == "state":
        first = boxes[nodes[0]["id"]]
        last = boxes[nodes[-1]["id"]]
        out.extend(
            [
                f'<circle cx="{first[0] + 160}" cy="32" r="8" class="solid"/>',
                line(first[0] + 160, 40, first[0] + 160, first[1], "rule"),
                f'<circle cx="{last[0] + 160}" cy="{last[1] + last[3] + 48}" r="12" class="box"/>',
                f'<circle cx="{last[0] + 160}" cy="{last[1] + last[3] + 48}" r="6" class="solid"/>',
                line(last[0] + 160, last[1] + last[3], last[0] + 160, last[1] + last[3] + 36),
            ]
        )
    return width, height, "\n".join(out)


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


def render(spec):
    validate(spec)
    width, height, body = render_svg(spec)
    links = "\n".join(
        f'<li><a href="#node-{esc(n["id"])}">{esc(n["label"])}: '
        f"{esc(', '.join(n.get('spec_ids', [])) or 'no spec IDs')}</a></li>"
        for n in spec["nodes"]
    )
    shell = (ASSETS / f"{spec['type']}.html").read_text(encoding="utf-8")
    for key, value in (("title", esc(spec["title"])), ("body", body), ("links", links)):
        shell = re.sub(
            rf"<!--{key}-->.*?<!--/{key}-->",
            lambda _, key=key, value=value: f"<!--{key}-->{value}<!--/{key}-->",
            shell,
            flags=re.S,
        )
    shell = re.sub(
        r'(?<=<svg )viewBox="[^"]*"(?: width="[^"]*")?',
        f'viewBox="0 0 {width} {height}" width="{width}"',
        shell,
    )
    shell = re.sub(r'(<marker[^>]*viewBox=")[^"]*', r"\g<1>0 0 10 10", shell)
    return shell, mermaid(spec)
