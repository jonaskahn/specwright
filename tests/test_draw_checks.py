"""Keep offline and border checks reusable for both assets and rendered files."""

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/sw-draw/scripts"
sys.path.insert(0, str(SCRIPTS))


def module(name):
    spec = importlib.util.spec_from_file_location("draw_" + name, SCRIPTS / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


BORDERS = module("check_borders")
OFFLINE = module("check_offline")


class DrawCheckTests(unittest.TestCase):
    def run_check(self, tool, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = tool.main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_every_template_passes_both_checks(self):
        assets = ROOT / "skills/sw-draw/assets"
        self.assertEqual(len(list(assets.glob("*.html"))), 8)
        for path in assets.glob("*.html"):
            for tool in (BORDERS, OFFLINE):
                self.assertEqual(self.run_check(tool, str(path)), (0, "", ""))

    def test_css_blocks_and_inline_styles_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.html"
            path.write_text(
                "<style>.a {border-inline-start:2px solid red}</style>\n"
                '<div style="border-top:1px solid red"></div>'
            )
            code, stdout, stderr = self.run_check(BORDERS, str(path))
            self.assertEqual(code, 1)
            self.assertIn(f"{path}:1: L-024", stdout)
            self.assertIn(f"{path}:2: L-024", stdout)
            self.assertFalse(stderr)
            path.write_text("<style>.a {border:1px solid red}</style><svg><line/></svg>")
            self.assertEqual(self.run_check(BORDERS, directory), (0, "", ""))

    def test_offline_rejects_remote_and_active_inputs(self):
        for raw in (
            "https://example.test",
            "http://example.test",
            "<script >",
            '<LINK href="local.css">',
            '@import "local.css"',
            "@font-face {font-family: remote}",
            '<img src="//example.test/x">',
            '<image href="local.svg">',
            "url(//remote)",
            "https&#58;//remote",
            '<svg onload="alert(1)">',
        ):
            with self.subTest(raw=raw):
                self.assertTrue(OFFLINE.check_text(raw))
        self.assertFalse(OFFLINE.check_text('<a href="#node-paid">Paid</a>'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.html"
            path.write_text("<script>bad</script>")
            code, stdout, stderr = self.run_check(OFFLINE, str(path))
            self.assertEqual(code, 1)
            self.assertIn(":1: OFFLINE", stdout)
            self.assertFalse(stderr)

    def test_missing_unsupported_and_non_utf8_paths_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            for tool in (BORDERS, OFFLINE):
                for name, data in (("bad.bin", b""), ("bad.html", b"\xff")):
                    path = Path(directory) / name
                    path.write_bytes(data)
                    code, stdout, stderr = self.run_check(tool, str(path))
                    self.assertEqual(code, 2)
                    self.assertFalse(stdout)
                    self.assertTrue(stderr)
                self.assertEqual(self.run_check(tool, str(Path(directory) / "absent.html"))[0], 2)


if __name__ == "__main__":
    unittest.main()
