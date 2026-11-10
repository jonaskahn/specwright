"""Full-catalog coverage: notation contracts, numerical fidelity and distribution."""

import copy
import importlib.util
import io
import json
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/sw-draw/scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("catalog_draw", SCRIPTS / "render_diagram.py")
DRAW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRAW)
from check_offline import check_text  # noqa: E402
from draw_page import standalone  # noqa: E402

from kitlib.borders import find_one_sided  # noqa: E402


def fixture(kind):
    path = (
        ROOT
        / ("fixtures/refund/diagrams" if kind in DRAW.LEGACY else "fixtures/draw")
        / f"{kind}.json"
    )
    return json.loads(path.read_text())


class CatalogTests(unittest.TestCase):
    def test_full_roster_and_every_structured_type(self):
        self.assertEqual(len(set(DRAW.TYPES)), 45)
        self.assertEqual(len(DRAW.STRUCTURED), 41)
        for kind in DRAW.STRUCTURED:
            with self.subTest(kind=kind):
                spec = fixture(kind)
                page, source = DRAW.render(spec)
                self.assertEqual((page, source), DRAW.render(copy.deepcopy(spec)))
                self.assertEqual(source is not None, kind in DRAW.MERMAID)
                self.assertFalse(check_text(page))
                self.assertFalse(find_one_sided(page))
                svg = standalone(page)
                self.assertFalse(check_text(svg))
                self.assertIn("<style>", svg)
                self.assertIn("prefers-color-scheme:dark", svg)
                tree = ET.fromstring(svg)
                self.assertEqual(tree.tag, "{http://www.w3.org/2000/svg}svg")
                for node in spec["nodes"]:
                    self.assertIn("node-" + node["id"], svg)
                    for ref in node.get("spec_ids", []):
                        self.assertIn(ref, svg)
                boxes = list(DRAW.layout(spec).values())
                for i, (x, y, w, h) in enumerate(boxes):
                    for xx, yy, ww, hh in boxes[i + 1 :]:
                        self.assertTrue(x + w <= xx or xx + ww <= x or y + h <= yy or yy + hh <= y)

    def test_template_routes_refuse_json_without_writing(self):
        for kind in DRAW.TEMPLATES:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "template"):
                DRAW.render({"type": kind})
            page = (SCRIPTS.parent / f"assets/{kind}-template.html").read_text()
            self.assertFalse(check_text(page))
            ET.fromstring(standalone(page))

    def test_hostile_input_and_unknown_fields_fail_for_every_new_type(self):
        for kind in set(DRAW.STRUCTURED) - set(DRAW.LEGACY):
            for bad in ("<script>evil</script>", "https://remote.test", "@import bad", "x\ny"):
                spec = fixture(kind)
                spec["nodes"][0]["label"] = bad
                with self.subTest(kind=kind, bad=bad), self.assertRaises(ValueError):
                    DRAW.render(spec)
            for key in ("html", "coordinates", "script"):
                spec = fixture(kind)
                spec[key] = "anything"
                with self.subTest(kind=kind, key=key), self.assertRaises(ValueError):
                    DRAW.render(spec)
            spec = fixture(kind)
            spec["nodes"][0]["spec_ids"] = ["BR-9999"]
            with self.assertRaises(ValueError):
                DRAW.render(spec)

    def test_invalid_numbers_dates_relations_and_malformed_data(self):
        cases = [
            ("bar", "value", float("nan")),
            ("bar", "value", float("inf")),
            ("bar", "value", True),
            ("gantt", "end", "2025-01-01"),
            ("timeline", "date", "next week"),
            ("sankey", "stage", 99),
            ("quadrant", "x", 2),
        ]
        for kind, key, value in cases:
            spec = fixture(kind)
            spec["nodes"][0][key] = value
            with self.subTest(kind=kind, key=key), self.assertRaises(ValueError):
                DRAW.render(spec)
        for kind in ("tree", "org-chart"):
            spec = fixture(kind)
            spec["edges"].append({"from": "n5", "to": "n1", "label": "cycle"})
            with self.assertRaises(ValueError):
                DRAW.render(spec)
        spec = fixture("sankey")
        spec["edges"][0]["weight"] = 41
        with self.assertRaisesRegex(ValueError, "balance"):
            DRAW.render(spec)
        for value in ([], None, {}, "bad"):
            with self.assertRaises(ValueError):
                DRAW.render(value)

    def test_paragraph_gate_never_writes(self):
        for kind in DRAW.STRUCTURED:
            spec = fixture(kind)
            spec["actors"] = ["Reader"]
            spec["nodes"] = spec["nodes"][:2]
            spec["edges"] = []
            with self.subTest(kind=kind), self.assertRaises(DRAW.ParagraphRequired):
                DRAW.render(spec)

    def test_direct_mermaid_grammars(self):
        prefixes = {
            "timeline": "timeline",
            "gantt": "gantt",
            "quadrant": "quadrantChart",
            "tree": "mindmap",
        }
        for kind, prefix in prefixes.items():
            source = DRAW.render(fixture(kind))[1]
            self.assertTrue(source.startswith(prefix))
            self.assertIn("BR", source)
        tree = DRAW.render(fixture("tree"))[1].splitlines()
        self.assertGreater(
            len(tree[-1]) - len(tree[-1].lstrip()), len(tree[1]) - len(tree[1].lstrip())
        )

    def test_variants_render_distinct_notation(self):
        variants = {
            "bar": ["dumbbell"],
            "pyramid": ["funnel"],
            "treemap": ["marimekko"],
            "line": ["slopegraph", "ridgeline", "streamgraph", "bump"],
            "scatter": ["bubble", "beeswarm", "box-plot"],
        }
        for kind, choices in variants.items():
            for variant in choices:
                spec = fixture(kind)
                spec["variant"] = variant
                for n in spec["nodes"]:
                    if variant == "dumbbell":
                        n["compare"] = n["value"] / 2
                    if variant == "marimekko":
                        n["segments"] = [3, 4, 5]
                    if variant == "bubble":
                        n["size"] = 64
                    if variant == "box-plot":
                        n["samples"] = [0.1, 0.2, 0.4, 0.6, 0.9]
                    if variant == "slopegraph":
                        n["values"] = n["values"][:2]
                if variant == "slopegraph":
                    spec["categories"] = spec["categories"][:2]
                with self.subTest(variant=variant):
                    page, _ = DRAW.render(spec)
                    self.assertFalse(check_text(page))
                    self.assertNotEqual(page, DRAW.render(fixture(kind))[0])

    def test_motion_is_bounded_and_complete(self):
        for mode in ("none", "reveal", "loop"):
            spec = fixture("process")
            spec["motion"] = mode
            page, _ = DRAW.render(spec)
            self.assertIn("motion-" + mode, page)
            self.assertIn("prefers-reduced-motion:reduce", page)
            self.assertIn("@media print", page)
            self.assertNotIn("<script", page)
            self.assertNotIn("infinite", page)
            self.assertNotIn("opacity:0", page)
            for n in spec["nodes"]:
                self.assertIn(n["label"], page)
        spec["motion"] = "javascript"
        with self.assertRaises(ValueError):
            DRAW.render(spec)

    def test_svg_cli_and_sidecar_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_text(json.dumps(fixture("timeline")))
            output = Path(directory) / "diagram.svg"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(DRAW.main([str(source), str(output)]), 0)
            ET.fromstring(output.read_text())
            self.assertTrue(output.with_suffix(".mmd").exists())
            output.unlink()
            output.with_suffix(".mmd").unlink()
            output.with_suffix(".mmd").mkdir()
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(DRAW.main([str(source), str(output)]), 2)
            self.assertFalse(output.exists())

    def test_delta_snapshots_and_exact_svg_values(self):
        spec = fixture("architecture-delta")
        spec["edges"][0]["snapshot"] = "after"
        page, _ = DRAW.render(spec)
        self.assertIn("BEFORE", page)
        self.assertIn("AFTER", page)
        self.assertIn("Manual decision", page)
        self.assertIn("Evidence-backed decision", page)
        self.assertIn('id="after-node-n3"', page)
        self.assertIn('id="node-n2"', page)
        self.assertNotIn('id="after-node-n4"', page)
        spec["edges"][0]["snapshot"] = "imagined"
        with self.assertRaises(ValueError):
            DRAW.render(spec)
        svg = standalone(DRAW.render(fixture("bar"))[0])
        for value in (12, 24, 18, 30, 16):
            self.assertIn(f"value: {value}", svg)

    def test_validator_rejects_catalog_and_asset_drift(self):
        import shutil

        from tests.test_validate import validate

        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sw-draw"
            shutil.copytree(
                SCRIPTS.parent, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
            for relative, code in (
                ("references/type-radar.md", "V122"),
                ("assets/bar.html", "V123"),
                ("scripts/draw_types/sankey.py", "V127"),
            ):
                target = skill / relative
                content = target.read_text()
                target.unlink()
                report = validate.Report(skill)
                validate._check_draw_contract(skill, report)
                self.assertIn(code, {f.code for f in report.errors})
                target.write_text(content)
            target = skill / "assets/bar.html"
            target.write_text(target.read_text().replace("--sw-bg:#ffffff", "--sw-bg:#eeeeee"))
            report = validate.Report(skill)
            validate._check_draw_contract(skill, report)
            self.assertIn("V124", {f.code for f in report.errors})

    def test_markers_retain_their_own_viewbox(self):
        for kind in DRAW.STRUCTURED:
            page, _ = DRAW.render(fixture(kind))
            for value in re.findall(r'<marker[^>]*viewBox="([^"]+)"', page):
                self.assertLessEqual(float(value.split()[2]), 16)


if __name__ == "__main__":
    unittest.main()
