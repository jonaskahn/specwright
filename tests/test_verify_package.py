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

    def test_empty_distribution_folder_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertTrue(verify.verify_zips(Path(raw)))


if __name__ == "__main__":
    unittest.main()
