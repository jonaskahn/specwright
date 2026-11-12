"""Geometry, encoding and drift checks for the trace-sheet drawing renderer."""

import copy
import json
import math
import re
import sys
import unittest

from tests.draw_full import ROOT, SCRIPTS, SHELLS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
draw_shells = SHELLS

import draw_engine  # noqa: E402
import render_diagram as DRAW  # noqa: E402
from draw_layout import measure, nice_ticks, overlaps, squarify, wrap  # noqa: E402

FLOW = (
    "process",
    "data-flow",
    "dp-integration",
    "dependency",
    "architecture",
    "deployment",
    "it-current-state",
    "tree",
    "org-chart",
    "uml-class",
    "db-schema",
    "flowchart",
    "swimlane",
    "state",
    "er",
)


def fixture(kind):
    return json.loads(draw_shells.fixture(kind).read_text())


def stress():
    """Long edges, a fork, a join and a cycle exercise dummy slots and back edges."""
    spec = fixture("dependency")
    names = ["Intake", "Policy", "Review", "Ledger", "Notice", "Audit"]
    spec["nodes"] = [
        {
            "id": f"n{i + 1}",
            "label": name,
            "spec_ids": ["BR-001"] if i == 0 else [],
            "version": "v1",
        }
        for i, name in enumerate(names)
    ]
    pairs = [(1, 2), (1, 3), (2, 4), (3, 4), (1, 4), (4, 5), (5, 2), (1, 6), (6, 5)]
    spec["edges"] = [
        {"from": f"n{a}", "to": f"n{b}", "label": f"hand-off {a} to {b}"} for a, b in pairs
    ]
    return spec


def segments(points):
    return list(zip(points, points[1:], strict=False))


def crosses_interior(seg, rect, margin=1.5):
    (ax, ay), (bx, by) = seg
    x0, x1 = min(ax, bx), max(ax, bx)
    y0, y1 = min(ay, by), max(ay, by)
    return not (
        x1 <= rect[0] + margin
        or x0 >= rect[0] + rect[2] - margin
        or y1 <= rect[1] + margin
        or y0 >= rect[1] + rect[3] - margin
    )


class FlowGeometry(unittest.TestCase):
    def specs(self):
        for kind in FLOW:
            yield kind, fixture(kind)
        yield "stress", stress()

    def test_tickets_never_overlap_cards_or_each_other(self):
        for name, spec in self.specs():
            cv = draw_engine.build(spec)
            with self.subTest(kind=name):
                for i, t in enumerate(cv.ticket_rects):
                    for rect in cv.node_rects:
                        self.assertFalse(overlaps(t, rect), (t, rect))
                    for other in cv.ticket_rects[i + 1 :]:
                        self.assertFalse(overlaps(t, other), (t, other))

    def test_no_connector_crosses_a_card_it_does_not_touch(self):
        for name, spec in self.specs():
            cv = draw_engine.build(spec)
            with self.subTest(kind=name):
                for points in cv.routes:
                    for seg in segments(points):
                        for rect in cv.node_rects:
                            if crosses_interior(seg, rect):
                                # A route may end on a card edge, never run through a body.
                                (ax, ay), (bx, by) = seg
                                inside = (
                                    rect[0] + 2 < ax < rect[0] + rect[2] - 2
                                    and rect[1] + 2 < ay < rect[1] + rect[3] - 2
                                ) or (
                                    rect[0] + 2 < bx < rect[0] + rect[2] - 2
                                    and rect[1] + 2 < by < rect[1] + rect[3] - 2
                                )
                                self.assertFalse(inside, (name, seg, rect))

    def test_connectors_are_orthogonal_and_never_stack(self):
        for name, spec in self.specs():
            cv = draw_engine.build(spec)
            with self.subTest(kind=name):
                for points in cv.routes:
                    for (ax, ay), (bx, by) in segments(points):
                        self.assertTrue(abs(ax - bx) < 0.01 or abs(ay - by) < 0.01)
                flat = [(i, s) for i, p in enumerate(cv.routes) for s in segments(p)]
                for i, (ei, a) in enumerate(flat):
                    for ej, b in flat[i + 1 :]:
                        if ei == ej:
                            continue
                        for axis in (0, 1):
                            other = 1 - axis
                            same_line = (
                                abs(a[0][axis] - a[1][axis]) < 0.01
                                and abs(b[0][axis] - b[1][axis]) < 0.01
                                and abs(a[0][axis] - b[0][axis]) < 0.5
                            )
                            if same_line:
                                lo = max(
                                    min(a[0][other], a[1][other]), min(b[0][other], b[1][other])
                                )
                                hi = min(
                                    max(a[0][other], a[1][other]), max(b[0][other], b[1][other])
                                )
                                self.assertLessEqual(hi - lo, 1.0, (name, a, b))

    def test_ports_on_one_edge_are_at_least_twelve_apart(self):
        cv = draw_engine.build(stress())
        starts = sorted(p[0] for p in cv.routes if p)
        by_y = {}
        for x, y in starts:
            by_y.setdefault(round(y), []).append(x)
        for xs in by_y.values():
            xs.sort()
            for a, b in zip(xs, xs[1:], strict=False):
                self.assertGreaterEqual(b - a, 11.9)

    def test_drawings_are_deterministic(self):
        for name, spec in self.specs():
            with self.subTest(kind=name):
                self.assertEqual(DRAW.render(copy.deepcopy(spec)), DRAW.render(spec))


class Encodings(unittest.TestCase):
    def classes(self, kind, **changes):
        spec = fixture(kind)
        spec.update(changes)
        page, _ = DRAW.render(spec)
        return page

    def test_single_series_bars_use_one_colour(self):
        page = self.classes("bar")
        rects = re.findall(r'<rect[^>]*class="(series-\d)[ "]', page)
        self.assertEqual(len(rects), 5)
        self.assertEqual(set(rects), {"series-1"})

    def test_heatmap_uses_only_the_ordered_ramp(self):
        page = self.classes("heatmap")
        cells = re.findall(r'<rect[^>]*class="(ramp-\d|series-\d)[ "]', page)
        self.assertTrue(cells)
        self.assertTrue(all(c.startswith("ramp-") for c in cells))
        values = {"n1": 1, "n2": 2, "n3": 3, "n4": 4, "n5": 5}
        steps = {n: int(s) for n, s in re.findall(r'id="node-(n\d)".*?class="ramp-(\d)', page)}
        self.assertEqual(sorted(steps, key=steps.get), sorted(values, key=values.get))

    def test_waterfall_classes_follow_the_sign_of_each_step(self):
        spec = fixture("waterfall")
        for node, value, total in zip(
            spec["nodes"], (100, -30, 20, 90, -10), (True, False, False, True, False), strict=True
        ):
            node["value"] = value
            node["total"] = total
        page, _ = DRAW.render(spec)
        classes = re.findall(r'<rect[^>]*class="(up|down|total) enter', page)
        self.assertEqual(classes, ["total", "down", "up", "total", "down"])
        self.assertIn("−30", page)
        self.assertIn("+20", page)

    def test_nice_ticks_cover_the_range_on_round_steps(self):
        for low, high in ((0, 30), (0, 7), (-40, 120), (0, 0.9), (0, 1_000_000)):
            ticks, lo, hi = nice_ticks(low, high)
            self.assertLessEqual(lo, low)
            self.assertGreaterEqual(hi, high)
            step = ticks[1] - ticks[0]
            mantissa = step / 10 ** math.floor(math.log10(step))
            self.assertTrue(any(abs(mantissa - m) < 1e-9 for m in (1, 2, 5)), step)

    def test_squarified_areas_are_proportional_and_tile_the_frame(self):
        values = [30, 24, 18, 16, 12]
        rects = squarify(values, 0, 0, 760, 400)
        total = sum(values)
        for v, (_x, _y, w, h) in zip(values, rects, strict=True):
            self.assertAlmostEqual(w * h, 760 * 400 * v / total, places=3)
        self.assertAlmostEqual(sum(w * h for _, _, w, h in rects), 760 * 400, places=3)
        for i, a in enumerate(rects):
            for b in rects[i + 1 :]:
                self.assertFalse(overlaps(a, b, -0.01))

    def test_measure_and_wrap_never_drop_text(self):
        text = "Evidence-backed decision for a very long refund category name"
        lines = wrap(text, 120, 15, True)
        self.assertEqual("".join(lines).replace(" ", ""), text.replace(" ", ""))
        self.assertGreater(measure("WWWW", 15), measure("iiii", 15))

    def test_focal_is_explicit_and_capped_at_two(self):
        page = self.classes("process")
        self.assertNotIn("box focal", page)
        spec = fixture("process")
        spec["nodes"][0]["focal"] = True
        self.assertIn("box focal", DRAW.render(spec)[0])
        for n in spec["nodes"][:3]:
            n["focal"] = True
        with self.assertRaises(ValueError):
            DRAW.render(spec)


class ShippedExamples(unittest.TestCase):
    def test_every_shipped_example_matches_a_fresh_render(self):
        stale = [
            str(path.relative_to(ROOT))
            for path, content in draw_shells.expected().items()
            if not path.is_file() or path.read_text(encoding="utf-8") != content
        ]
        self.assertEqual(stale, [], "run: python3 workshop/tools/draw_shells.py --write")

    def test_pages_have_one_figure_one_title_and_no_ledger_noise(self):
        for kind in DRAW.STRUCTURED:
            page, _ = DRAW.render(fixture(kind))
            with self.subTest(kind=kind):
                self.assertEqual(page.count("<svg"), 1)
                self.assertEqual(page.count("<h1>"), 1)
                self.assertNotIn("see data table", page)
                self.assertNotIn("Connections, changes", page)


if __name__ == "__main__":
    unittest.main()
