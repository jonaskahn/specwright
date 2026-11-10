"""Check that source data remains inert and diagrams remain reproducible."""

import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/sw-draw/scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_SPEC = importlib.util.spec_from_file_location("draw_renderer", SCRIPTS / "render_diagram.py")
DRAW = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(DRAW)
FIXTURES = ROOT / "fixtures/refund/diagrams"


class DrawRenderTests(unittest.TestCase):
    def fixture(self, kind="state"):
        return json.loads((FIXTURES / f"{kind}.json").read_text())

    def run_main(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = DRAW.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_refund_is_deterministic_visible_and_offline(self):
        spec = self.fixture()
        first = DRAW.render(spec)
        self.assertEqual(first, DRAW.render(copy.deepcopy(spec)))
        for item in (
            "Submitted",
            "Pending approval",
            "Approved",
            "Rejected",
            "Paid",
            "BR-001",
            "AC-001-3",
            "Spec links",
            'data-spec="AC-001-3"',
        ):
            self.assertIn(item, first[0])
        self.assertNotIn("http", first[0])
        self.assertIn("stateDiagram-v2", first[1])

    def test_all_types_have_disjoint_node_boxes_and_companions(self):
        for kind in DRAW.LEGACY:
            with self.subTest(kind=kind):
                spec = self.fixture(kind)
                page, source = DRAW.render(spec)
                boxes = list(DRAW.layout(spec).values())
                for i, (x, y, w, h) in enumerate(boxes):
                    for xx, yy, ww, hh in boxes[i + 1 :]:
                        self.assertTrue(x + w <= xx or xx + ww <= x or y + h <= yy or yy + hh <= y)
                self.assertEqual(source is not None, kind in DRAW.MERMAID)
                self.assertRegex(page, r"prefers-color-scheme\s*:\s*dark")
                self.assertRegex(page, r"paint-order\s*:\s*stroke")
                self.assertIn('role="img"', page)

    def test_plain_hostile_punctuation_is_escaped(self):
        spec = self.fixture()
        spec["nodes"][0]["label"] = 'A & "B" > C'
        page, source = DRAW.render(spec)
        self.assertIn("A &amp; &quot;B&quot; &gt; C", page)
        self.assertNotIn('A & "B" > C', page)
        self.assertIn("#34;", source)
        for hostile in (
            "<script>alert(1)</script>",
            "<b>Paid</b>",
            "https://remote.test",
            "x\ny",
            "@import evil",
        ):
            spec["nodes"][0]["label"] = hostile
            with self.subTest(hostile=hostile), self.assertRaises(ValueError):
                DRAW.render(spec)

    def test_invalid_spec_fields_fail_closed(self):
        variants = []
        for field, value in (
            ("type", "architecture"),
            ("nodes", []),
            ("title", ""),
            ("edges", [{"from": "missing", "to": "paid", "label": "go"}]),
        ):
            spec = self.fixture()
            spec[field] = value
            variants.append(spec)
        for field, value in (("id", "paid"), ("spec_ids", ["BR-9999"]), ("actor", "Unknown")):
            spec = self.fixture()
            spec["nodes"][0][field] = value
            variants.append(spec)
        for spec in variants:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                DRAW.render(spec)
        journey = self.fixture("journey")
        del journey["nodes"][0]["feeling"]
        with self.assertRaises(ValueError):
            DRAW.render(journey)
        entity = self.fixture("er")
        entity["edges"][0]["to_card"] = "manyish"
        with self.assertRaises(ValueError):
            DRAW.render(entity)

    def test_cli_success_refusal_bad_json_and_io_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "input.json", root / "output.html"
            source.write_text(json.dumps(self.fixture()))
            code, stdout, stderr = self.run_main([str(source), str(output)])
            self.assertEqual(code, 0)
            self.assertIn(str(output), stdout)
            self.assertFalse(stderr)
            self.assertTrue(output.with_suffix(".mmd").is_file())
            before = output.read_bytes()
            self.assertEqual(self.run_main([str(source), str(output)])[0], 0)
            self.assertEqual(before, output.read_bytes())
            small = self.fixture()
            small["nodes"] = small["nodes"][:3]
            small["edges"] = []
            source.write_text(json.dumps(small))
            refused = root / "refused.html"
            code, stdout, stderr = self.run_main([str(source), str(refused)])
            self.assertEqual(code, 3)
            self.assertIn("write a paragraph", stderr)
            self.assertFalse(stdout)
            self.assertFalse(refused.exists())
            for raw in ("{", "[]", '{"type":"state"}'):
                source.write_text(raw)
                self.assertEqual(self.run_main([str(source), str(output)])[0], 2)
            self.assertEqual(self.run_main([str(root / "absent.json"), str(output)])[0], 2)
            source.write_text(json.dumps(self.fixture()))
            directory_output = root / "folder.html"
            directory_output.mkdir()
            self.assertEqual(self.run_main([str(source), str(directory_output)])[0], 2)
            self.assertEqual(self.run_main([str(source), str(source)])[0], 2)

    def test_html_only_cli_does_not_create_mermaid(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "blueprint.html"
            code, _, _ = self.run_main([str(FIXTURES / "service-blueprint.json"), str(output)])
            self.assertEqual(code, 0)
            self.assertFalse(output.with_suffix(".mmd").exists())
            self.assertIn("n/a", output.read_text())

    def test_help_and_usage_are_real_cli_exit_codes(self):
        for name in ("render_diagram", "check_borders", "check_offline"):
            for args, expected in ((["--help"], 0), ([], 2)):
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS / f"{name}.py"), *args],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
