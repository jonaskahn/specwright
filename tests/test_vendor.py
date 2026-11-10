import importlib.util
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "vendor", Path(__file__).resolve().parent.parent / "tools" / "vendor.py"
)
vendor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vendor)


class VendorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "lib/kitlib").mkdir(parents=True)
        (self.root / "lib/kitlib/__init__.py").write_text("VALUE = 1\n")
        (self.root / "lib/shared-references").mkdir(parents=True)
        (self.root / "lib/shared-references/stop-and-ask.md").write_text("ask\n")
        (self.root / "LICENSE").write_text("MIT\n")
        (self.root / "AGENTS.md").write_text("# Rules\n")
        self.skill = self.root / "skills/sw-demo"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# demo\n")
        (self.root / "skills/sw-init/assets").mkdir(parents=True)
        (self.root / "skills/sw-init/assets/standing-rules.md").write_text("# Rules\n")

    def test_write_is_idempotent_and_check_passes(self):
        vendor.write(self.root)
        first = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        vendor.write(self.root)
        second = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(first, second)
        self.assertEqual(vendor.check(self.root), [])

    def test_check_rejects_missing_divergent_and_extra_files(self):
        vendor.write(self.root)
        (self.skill / "scripts/kitlib/__init__.py").unlink()
        (self.skill / "references/stop-and-ask.md").write_text("different\n")
        (self.skill / "scripts/kitlib/extra.py").write_text("x = 1\n")
        problems = vendor.check(self.root)
        self.assertTrue(any("missing vendored file" in item for item in problems))
        self.assertTrue(any("divergent vendored file" in item for item in problems))
        self.assertTrue(any("unexpected vendored file" in item for item in problems))

    def test_write_removes_unexpected_vendored_files(self):
        vendor.write(self.root)
        extra = self.skill / "scripts/kitlib/extra.py"
        extra.write_text("x = 1\n")
        vendor.write(self.root)
        self.assertFalse(extra.exists())

    def test_shared_reference_and_license_are_required(self):
        vendor.write(self.root)
        (self.skill / "LICENSE").unlink()
        (self.skill / "references/stop-and-ask.md").write_text("changed\n")
        problems = vendor.check(self.root)
        self.assertIn(f"missing vendored file: {self.skill / 'LICENSE'}", problems)
        self.assertIn(
            f"divergent vendored file: {self.skill / 'references/stop-and-ask.md'}", problems
        )

    def test_write_embeds_drawing_theme_bytes(self):
        assets = self.root / "skills/sw-draw/assets"
        assets.mkdir(parents=True)
        theme = "\n:root { --sw-bg: #fff; }\n"
        (assets / "theme.css").write_text(theme)
        shell = assets / "er.html"
        shell.write_text(
            "<html><style>\n        :root { --sw-bg: #000; }\n"
            "        svg {\n            max-width: none;\n"
            "            min-width: 960px;\n        }\n    </style></html>\n"
        )
        vendor.write(self.root)
        text = shell.read_text()
        self.assertIn(theme, text)
        self.assertIn("min-width: 960px", text)
        self.assertEqual(vendor.check(self.root), [])


if __name__ == "__main__":
    unittest.main()
