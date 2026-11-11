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

from tests.draw_full import ROOT, SCRIPTS, SHELLS  # noqa: E402

sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("catalog_draw", SCRIPTS / "render_diagram.py")
DRAW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DRAW)
from check_offline import check_text  # noqa: E402
from draw_page import standalone  # noqa: E402
from draw_types import EXTENDED  # noqa: E402

from kitlib.borders import find_one_sided  # noqa: E402


def fixture(kind):
    return json.loads(SHELLS.fixture(kind).read_text())


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
                self.assertRegex(svg, r"prefers-color-scheme\s*:\s*dark")
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
            self.assertRegex(page, r"prefers-reduced-motion\s*:\s*reduce")
            self.assertIn("@media print", page)
            self.assertNotIn("<script", page)
            self.assertNotIn("infinite", page)
            for n in spec["nodes"]:
                self.assertIn(n["label"], page)
        spec["motion"] = "javascript"
        with self.assertRaises(ValueError):
            DRAW.render(spec)

    def test_motion_is_on_by_default_only_where_order_is_the_meaning(self):
        from draw_page import AUTO_MOTION

        self.assertEqual(
            set(AUTO_MOTION),
            {
                "process",
                "data-flow",
                "dp-integration",
                "flowchart",
                "swimlane",
                "state",
                "loop",
                "journey",
                "sequence",
                "bar",
                "waterfall",
                "gantt",
                "timeline",
                "sankey",
                "line",
            },
        )
        for kind in DRAW.STRUCTURED:
            page, _ = DRAW.render(fixture(kind))
            match = re.search(r"drawing motion-(\w+)", page)
            expected = AUTO_MOTION.get(kind, "none")
            with self.subTest(kind=kind):
                self.assertEqual(match.group(1), expected)
                # Playback is finite; the theme hides only the decorative token at rest.
                for count in re.findall(r"linear \d+ms (\d+)\b", page) + re.findall(
                    r"s linear 600ms (\d+)", page
                ):
                    self.assertLessEqual(int(count), 3)
                if expected == "none":
                    self.assertNotIn("@keyframes sw-flow", page)

    def test_flow_token_is_destination_coloured_and_stays_on_connectors(self):
        page, _ = DRAW.render(fixture("process"))
        css = re.search(r"@keyframes sw-flow\{(.*?)\}\n@supports", page, re.S).group(1)
        self.assertEqual(len(re.findall(r"offset-distance:100%;opacity:1", css)), 4)
        self.assertEqual({int(n) for n in re.findall(r"var\(--series-(\d)\)", css)}, {2, 3, 4, 5})
        for path in re.findall(r"offset-path:path\('([^']+)'\)", css):
            self.assertEqual(path.count("M"), 1)
            self.assertRegex(path, r"^M [\d. -]+[LQ ]")

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
            self.assertIn(f">{value}<", svg)

    def test_validator_rejects_catalog_and_asset_drift(self):
        import shutil

        from tests.test_validate import validate

        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sw-spec"
            shutil.copytree(
                SHELLS.SKILL, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )

            def codes(packaged=False):
                report = validate.Report(skill)
                validate._check_draw_contract(skill, ROOT, report, packaged)
                return {f.code for f in report.errors}

            self.assertEqual(codes(), set())
            for relative, code in (
                ("references/type-tree.md", "V122"),
                ("assets/kanban.html", "V123"),
                ("scripts/draw_types/gantt.py", "V127"),
            ):
                target = skill / relative
                content = target.read_text()
                target.unlink()
                self.assertIn(code, codes())
                target.write_text(content)
            target = skill / "assets/kanban.html"
            target.write_text(target.read_text().replace("--sw-bg: #f3f4f7", "--sw-bg: #eeeeee"))
            self.assertIn("V124", codes())

    def test_validator_keeps_extras_out_of_the_skill_and_tolerates_a_core_build(self):
        import shutil

        from tests.test_validate import validate

        with tempfile.TemporaryDirectory() as directory:
            skill = Path(directory) / "sw-spec"
            shutil.copytree(
                SHELLS.SKILL, skill, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
            parked = skill / "assets/bar.html"
            shutil.copy(SHELLS.EXTRAS / "assets/bar.html", parked)
            report = validate.Report(skill)
            validate._check_draw_contract(skill, ROOT, report)
            self.assertIn("V129", {f.code for f in report.errors})
            parked.unlink()
            for kind in EXTENDED:
                (skill / f"assets/{kind}.html").unlink()
                (skill / f"references/type-{kind}.md").unlink()
                (skill / f"scripts/draw_types/{kind.replace('-', '_')}.py").unlink()
            report = validate.Report(skill)
            validate._check_draw_contract(skill, ROOT, report, True)
            self.assertEqual([f.code for f in report.errors], [])
            report = validate.Report(skill)
            validate._check_draw_contract(skill, ROOT, report)
            self.assertIn("V122", {f.code for f in report.errors})

    def test_markers_retain_their_own_viewbox(self):
        for kind in DRAW.STRUCTURED:
            page, _ = DRAW.render(fixture(kind))
            for value in re.findall(r'<marker[^>]*viewBox="([^"]+)"', page):
                self.assertLessEqual(float(value.split()[2]), 16)

    def test_standalone_svg_is_one_flat_framed_sheet(self):
        import xml.dom.minidom

        for kind in DRAW.STRUCTURED:
            page, _ = DRAW.render(fixture(kind))
            svg = DRAW.standalone(page)
            self.assertIn('data-framed="1"', svg, kind)
            self.assertIn("--sw-surface", svg, kind)
            self.assertIn("translate(32 104)", svg, kind)
            self.assertNotIn("drop-shadow", svg, kind)
            self.assertNotIn("<filter", svg, kind)
            self.assertEqual(svg.count('class="sheet"'), 1, kind)
            self.assertNotIn('class="paper"', svg, kind)
            xml.dom.minidom.parseString(svg)


if __name__ == "__main__":
    unittest.main()
