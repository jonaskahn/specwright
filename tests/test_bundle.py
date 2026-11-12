import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
sys.path.insert(0, str(TOOLS))


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = load_tool("bundle")
package = load_tool("package")


class BundleFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / "repo"
        shared = self.root / "skills/_shared"
        (shared / "scripts/kitlib").mkdir(parents=True)
        (shared / "references").mkdir()
        (shared / "scripts/kitlib/__init__.py").write_text("")
        (shared / "scripts/kitlib/a.py").write_text(
            "def run():\n    from kitlib import b\n    return b\n"
        )
        (shared / "scripts/kitlib/b.py").write_text("VALUE = 1\n")
        (shared / "scripts/kitlib/unused.py").write_text("VALUE = 2\n")
        (shared / "scripts/lint.py").write_text("from kitlib.a import run\n")
        (shared / "references/core.md").write_text("core\n")
        (shared / "references/extra.md").write_text("extra\n")
        skill = self.root / "skills/sw-demo"
        (skill / "scripts").mkdir(parents=True)
        (skill / "SKILL.md").write_text("Read ../_shared/references/core.md.\n")
        (skill / "scripts/run.py").write_text("from kitlib import a\n")
        self.skill = skill
        self.write_map(
            {
                "limits": {"max_files": 200, "target_files": 190},
                "capabilities": {"quality": {"roots": ["scripts/lint.py"]}},
                "skills": {"sw-demo": {"capabilities": [], "shared": []}},
            }
        )

    def write_map(self, data):
        (self.root / "skills/_shared" / bundle.MAP_NAME).write_text(json.dumps(data))

    def read_map(self):
        return json.loads((self.root / "skills/_shared" / bundle.MAP_NAME).read_text())

    def set_skill(self, **fields):
        data = self.read_map()
        data["skills"]["sw-demo"].update(fields)
        self.write_map(data)


class DeriveTests(BundleFixture):
    def test_write_follows_imports_through_functions_and_text_references(self):
        self.assertEqual(bundle.write(self.root), ["sw-demo"])
        shared = self.read_map()["skills"]["sw-demo"]["shared"]
        self.assertEqual(
            shared,
            [
                "references/core.md",
                "scripts/kitlib/__init__.py",
                "scripts/kitlib/a.py",
                "scripts/kitlib/b.py",
            ],
        )
        self.assertEqual(bundle.check(self.root), ([], []))

    def test_capability_roots_pull_in_their_python_closure(self):
        self.set_skill(capabilities=["quality"])
        bundle.write(self.root)
        shared = self.read_map()["skills"]["sw-demo"]["shared"]
        self.assertIn("scripts/lint.py", shared)
        self.assertNotIn("scripts/kitlib/unused.py", shared)

    def test_write_is_idempotent(self):
        bundle.write(self.root)
        self.assertEqual(bundle.write(self.root), [])


class CheckTests(BundleFixture):
    def setUp(self):
        super().setUp()
        bundle.write(self.root)

    def test_omitted_file_is_reported_as_needed(self):
        stored = self.read_map()["skills"]["sw-demo"]["shared"]
        self.set_skill(shared=[s for s in stored if not s.endswith("b.py")])
        problems, _ = bundle.check(self.root)
        self.assertIn("sw-demo: needs scripts/kitlib/b.py but the map omits it", problems)

    def test_surplus_file_is_reported(self):
        stored = self.read_map()["skills"]["sw-demo"]["shared"]
        self.set_skill(shared=sorted([*stored, "references/extra.md"]))
        problems, _ = bundle.check(self.root)
        self.assertIn("sw-demo: ships references/extra.md but nothing needs it", problems)

    def test_missing_mapped_file_is_reported(self):
        (self.root / "skills/_shared/references/core.md").unlink()
        problems, _ = bundle.check(self.root)
        self.assertTrue(any("references/core.md" in p for p in problems))

    def test_unknown_capability_is_reported(self):
        self.set_skill(capabilities=["nope"])
        problems, _ = bundle.check(self.root)
        self.assertIn("sw-demo: unknown capability 'nope'", problems)

    def test_skill_without_entry_and_entry_without_skill_are_reported(self):
        data = self.read_map()
        data["skills"]["sw-ghost"] = {"capabilities": [], "shared": []}
        del data["skills"]["sw-demo"]
        self.write_map(data)
        problems, _ = bundle.check(self.root)
        self.assertIn("sw-ghost: in the map but not a public skill", problems)
        self.assertIn("sw-demo: has no entry in bundle-map.json", problems)

    def test_text_reference_to_a_missing_shared_file_is_reported(self):
        (self.skill / "SKILL.md").write_text("Read ../_shared/references/gone.md.\n")
        problems, _ = bundle.check(self.root)
        self.assertTrue(any("names missing references/gone.md" in p for p in problems))

    def test_file_cap_is_an_error_and_target_is_a_warning(self):
        data = self.read_map()
        data["limits"] = {"max_files": 6, "target_files": 5}
        self.write_map(data)
        problems, warnings = bundle.check(self.root)
        self.assertEqual(problems, [])
        self.assertTrue(any("above the target of 5" in w for w in warnings))
        data["limits"] = {"max_files": 5, "target_files": 5}
        self.write_map(data)
        problems, _ = bundle.check(self.root)
        self.assertTrue(any("exceed the cap of 5" in p for p in problems))

    def test_missing_map_fails_closed(self):
        (self.root / "skills/_shared" / bundle.MAP_NAME).unlink()
        problems, _ = bundle.check(self.root)
        self.assertEqual(problems, ["skills/_shared/bundle-map.json is missing"])

    def test_report_lists_each_skill_and_unshipped_files(self):
        text = bundle.report(self.root)
        self.assertIn("sw-demo", text)
        self.assertIn("shipped by no skill", text)
        self.assertIn("references/extra.md", text)


class PackageTests(BundleFixture):
    def setUp(self):
        super().setUp()
        bundle.write(self.root)
        self.output = self.base / "out"

    def test_only_mapped_shared_files_are_packaged(self):
        package.build(self.root, self.output)
        shipped = {
            p.relative_to(self.output / "sw-demo/_shared").as_posix()
            for p in (self.output / "sw-demo/_shared").rglob("*")
            if p.is_file() and p.name != "MANIFEST.json"
        }
        self.assertEqual(shipped, set(self.read_map()["skills"]["sw-demo"]["shared"]))
        self.assertTrue((self.output / "sw-demo/_shared/MANIFEST.json").is_file())
        self.assertNotIn("references/extra.md", shipped)
        self.assertFalse((self.output / "sw-demo/_shared" / bundle.MAP_NAME).exists())

    def test_oversize_skill_is_refused_before_anything_is_written(self):
        data = self.read_map()
        data["limits"]["max_files"] = 5
        self.write_map(data)
        with self.assertRaisesRegex(ValueError, "sw-demo would ship"):
            package.build(self.root, self.output, True)
        self.assertFalse(self.output.exists())

    def test_skill_missing_from_the_map_is_refused(self):
        data = self.read_map()
        del data["skills"]["sw-demo"]
        self.write_map(data)
        with self.assertRaisesRegex(ValueError, "has no entry"):
            package.build(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_map_is_refused(self):
        (self.root / "skills/_shared" / bundle.MAP_NAME).unlink()
        with self.assertRaisesRegex(ValueError, "bundle-map.json is missing"):
            package.build(self.root, self.output)

    def test_mapped_file_that_vanished_is_refused(self):
        (self.root / "skills/_shared/references/core.md").unlink()
        with self.assertRaisesRegex(ValueError, "mapped shared files are missing"):
            package.build(self.root, self.output)


class RepositoryTests(unittest.TestCase):
    def test_real_map_matches_the_source_tree_and_the_cap(self):
        problems, _ = bundle.check(REPO)
        self.assertEqual(problems, [])

    def test_every_public_skill_stays_under_the_upload_cap(self):
        data = bundle.load_map(REPO)
        cap = data["limits"]["max_files"]
        self.assertLessEqual(cap, 200)
        for skill in bundle.skill_folders(REPO):
            self.assertLessEqual(bundle.count_files(REPO, data, skill), cap, skill.name)

    def test_real_packages_contain_no_unmapped_shared_files(self):
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "dist"
            package.build(REPO, out)
            for skill in bundle.skill_folders(REPO):
                files = [p for p in (out / skill.name).rglob("*") if p.is_file()]
                self.assertLessEqual(len(files), 200, skill.name)
                self.assertFalse(any("__pycache__" in str(p) for p in files), skill.name)


class ProfileTests(BundleFixture):
    """A skill with extended diagram types builds a smaller core profile."""

    def setUp(self):
        super().setUp()
        for rel, text in (
            (
                "references/type-picker.md",
                "| Flow | references/type-flow.md |\n"
                "| Gantt | references/type-gantt.md |\nclosing line\n",
            ),
            ("references/type-flow.md", "flow\n"),
            ("references/type-gantt.md", "gantt\n"),
            ("assets/flow.html", "<p>flow</p>\n"),
            ("assets/gantt.html", "<p>gantt</p>\n"),
            ("scripts/draw_types/flow.py", "X = 1\n"),
            ("scripts/draw_types/gantt.py", "X = 2\n"),
        ):
            path = self.skill / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.set_skill(tiers={"extended": ["gantt"]})
        bundle.write(self.root)
        self.output = self.base / "out"

    def test_core_profile_leaves_extended_files_and_picker_rows_out(self):
        package.build(self.root, self.output, profile="core")
        built = self.output / "sw-demo"
        self.assertTrue((built / "assets/flow.html").is_file())
        for rel in ("assets/gantt.html", "references/type-gantt.md", "scripts/draw_types/gantt.py"):
            self.assertFalse((built / rel).exists(), rel)
        picker = (built / "references/type-picker.md").read_text()
        self.assertIn("type-flow.md", picker)
        self.assertNotIn("gantt", picker)
        self.assertIn("closing line", picker)

    def test_extended_profile_ships_everything(self):
        package.build(self.root, self.output, profile="extended")
        built = self.output / "sw-demo"
        self.assertTrue((built / "assets/gantt.html").is_file())
        self.assertIn("type-gantt.md", (built / "references/type-picker.md").read_text())

    def test_source_skill_is_never_modified_by_a_core_build(self):
        package.build(self.root, self.output, profile="core")
        self.assertTrue((self.skill / "assets/gantt.html").is_file())
        self.assertIn("gantt", (self.skill / "references/type-picker.md").read_text())

    def test_report_counts_each_profile_and_core_is_smaller(self):
        data = self.read_map()
        core = bundle.count_files(self.root, data, self.skill, "core")
        full = bundle.count_files(self.root, data, self.skill, "extended")
        self.assertEqual(full - core, 3)
        text = bundle.report(self.root)
        self.assertIn("sw-demo (core)", text)
        self.assertIn("sw-demo (extended)", text)

    def test_cap_is_checked_per_profile(self):
        data = self.read_map()
        core = bundle.count_files(self.root, data, self.skill, "core")
        data["limits"] = {"max_files": core, "target_files": core}
        self.write_map(data)
        problems, _ = bundle.check(self.root)
        self.assertTrue(any("(extended profile)" in p for p in problems))
        self.assertFalse(any("(core profile)" in p for p in problems))
        with self.assertRaisesRegex(ValueError, "extended profile"):
            package.build(self.root, self.output, profile="extended")
        self.assertTrue(package.build(self.root, self.output, profile="core"))

    def test_missing_extended_file_is_reported(self):
        (self.skill / "assets/gantt.html").unlink()
        problems, _ = bundle.check(self.root)
        self.assertTrue(any("extended type 'gantt' lacks assets/gantt.html" in p for p in problems))

    def test_unknown_profile_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown profile"):
            package.build(self.root, self.output, profile="tiny")


if __name__ == "__main__":
    unittest.main()
