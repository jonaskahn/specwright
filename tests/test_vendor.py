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
        (self.root / "skills/_shared/scripts/kitlib").mkdir(parents=True)
        (self.root / "skills/_shared/scripts/kitlib/__init__.py").write_text("VALUE = 1\n")
        (self.root / "skills/_shared/scripts/graph.py").write_text("print('graph')\n")
        (self.root / "skills/_shared/references").mkdir(parents=True)
        (self.root / "skills/_shared/references/stop-and-ask.md").write_text("ask\n")
        self.skill = self.root / "skills/sw-demo"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# demo\n")

    def test_source_layout_is_clean(self):
        self.assertEqual(vendor.check(self.root), [])
        self.assertEqual(vendor.write(self.root), [])

    def test_missing_shared_tree_is_reported(self):
        import shutil

        shutil.rmtree(self.root / "skills/_shared/scripts/kitlib")
        problems = vendor.check(self.root)
        self.assertIn("skills/_shared/scripts/kitlib is missing", problems)

    def test_source_skill_must_not_vendor_shared(self):
        (self.skill / "_shared").mkdir()
        problems = vendor.check(self.root)
        self.assertIn(f"source skill must not vendor _shared: {self.skill / '_shared'}", problems)

    def test_source_skill_must_not_vendor_kitlib(self):
        (self.skill / "scripts/kitlib").mkdir()
        problems = vendor.check(self.root)
        self.assertIn(
            f"source skill must not vendor kitlib: {self.skill / 'scripts/kitlib'}", problems
        )


if __name__ == "__main__":
    unittest.main()
