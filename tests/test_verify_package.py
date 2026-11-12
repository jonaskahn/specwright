import importlib.util
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load_tool("package")
verify = load_tool("verify_package")


class VerifyPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dist = Path(cls.tmp.name) / "dist"
        package.build(ROOT, cls.dist, zipped=True, profile="core")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_real_zip_is_self_contained(self):
        self.assertEqual(verify.verify_zips(self.dist), [])

    def test_a_skill_without_its_shared_folder_is_reported(self):
        with tempfile.TemporaryDirectory() as raw:
            with zipfile.ZipFile(self.dist / "sw-start.zip") as archive:
                archive.extractall(raw)
            skill = Path(raw) / "sw-start"
            shutil.rmtree(skill / "_shared")
            problems = verify.verify_skill(skill)
        self.assertTrue(
            any("scripts/start.py" in p and "shared library missing" in p for p in problems)
        )
        self.assertTrue(any("names missing" in p for p in problems))

    def test_a_changed_or_missing_shared_file_is_reported(self):
        with tempfile.TemporaryDirectory() as raw:
            with zipfile.ZipFile(self.dist / "sw-start.zip") as archive:
                archive.extractall(raw)
            skill = Path(raw) / "sw-start"
            (skill / "_shared/scripts/trace.py").write_text("# edited\n")
            (skill / "_shared/scripts/status.py").unlink()
            problems = verify.verify_skill(skill)
            (skill / "_shared/MANIFEST.json").unlink()
            unlisted = verify.verify_skill(skill)
        self.assertTrue(any("trace.py differs" in p for p in problems))
        self.assertTrue(any("status.py is missing" in p for p in problems))
        self.assertTrue(any("MANIFEST.json is missing" in p for p in unlisted))

    def test_each_source_skill_works_when_copied_alone(self):
        # `npx skills add` copies one skill folder, never its sibling skills/_shared.
        for source in sorted((ROOT / "skills").glob("sw-*")):
            with self.subTest(skill=source.name), tempfile.TemporaryDirectory() as raw:
                alone = Path(raw) / source.name
                shutil.copytree(source, alone, ignore=shutil.ignore_patterns("__pycache__"))
                self.assertEqual(verify.verify_skill(alone), [])

    def test_empty_distribution_folder_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertTrue(verify.verify_zips(Path(raw)))


if __name__ == "__main__":
    unittest.main()
