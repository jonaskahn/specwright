import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location("vendor", TOOLS / "vendor.py")
vendor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vendor)

MAPPED = ["references/stop-and-ask.md", "scripts/graph.py", "scripts/kitlib/__init__.py"]


class VendorTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        shared = self.root / "skills/_shared"
        (shared / "scripts/kitlib").mkdir(parents=True)
        (shared / "scripts/kitlib/__init__.py").write_text("VALUE = 1\n")
        (shared / "scripts/graph.py").write_text("print('graph')\n")
        (shared / "references").mkdir(parents=True)
        (shared / "references/stop-and-ask.md").write_text("ask\n")
        (shared / "bundle-map.json").write_text(
            json.dumps(
                {
                    "limits": {},
                    "capabilities": {},
                    "skills": {"sw-demo": {"capabilities": [], "shared": MAPPED}},
                }
            )
        )
        self.skill = self.root / "skills/sw-demo"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("# demo\n")

    def test_write_copies_exactly_the_mapped_files(self):
        self.assertEqual(vendor.write(self.root), ["sw-demo"])
        self.assertEqual(sorted(vendor.actual_files(self.skill)), MAPPED)
        self.assertEqual(vendor.check(self.root), [])
        self.assertEqual(vendor.write(self.root), [])

    def test_missing_copy_is_reported(self):
        problems = vendor.check(self.root)
        self.assertIn("sw-demo: _shared/scripts/graph.py is missing", problems)

    def test_different_and_extra_files_are_reported_and_repaired(self):
        vendor.write(self.root)
        (self.skill / "_shared/scripts/graph.py").write_text("changed\n")
        (self.skill / "_shared/references/old.md").write_text("stale\n")
        problems = vendor.check(self.root)
        self.assertIn(
            "sw-demo: _shared/scripts/graph.py differs from skills/_shared/scripts/graph.py",
            problems,
        )
        self.assertIn("sw-demo: _shared/references/old.md is not mapped", problems)
        vendor.write(self.root)
        self.assertEqual(vendor.check(self.root), [])

    def test_missing_shared_tree_is_reported(self):
        shutil.rmtree(self.root / "skills/_shared/scripts/kitlib")
        self.assertIn("skills/_shared/scripts/kitlib is missing", vendor.check(self.root))

    def test_source_skill_must_not_vendor_kitlib(self):
        vendor.write(self.root)
        (self.skill / "scripts/kitlib").mkdir()
        problems = vendor.check(self.root)
        self.assertIn(
            f"source skill must not vendor kitlib: {self.skill / 'scripts/kitlib'}", problems
        )

    def test_skill_without_a_map_entry_is_reported(self):
        other = self.root / "skills/sw-other"
        other.mkdir()
        (other / "SKILL.md").write_text("# other\n")
        self.assertTrue(any("sw-other" in p for p in vendor.check(self.root)))


if __name__ == "__main__":
    unittest.main()
