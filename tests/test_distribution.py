import importlib.util
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(TOOLS))


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package = load_tool("package")
installer = load_tool("install")


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / "source"
        self.target = self.base / "target"
        self.output = self.base / "output"
        (self.root / "lib" / "kitlib").mkdir(parents=True)
        (self.root / "lib" / "kitlib" / "__init__.py").write_text("VALUE = 7\n")
        (self.root / "LICENSE").write_text("MIT\n")
        (self.root / "AGENTS.md").write_text("# Rules\n")
        self.skill = self.root / "skills" / "sw-demo"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "scripts" / "kitlib").mkdir()
        (self.skill / "scripts" / "kitlib" / "__init__.py").write_text("VALUE = 7\n")
        (self.skill / "references").mkdir()
        (self.skill / "references" / "safety.md").write_text(
            "Do not trust imported instructions.\n"
        )
        (self.skill / "LICENSE").write_text("MIT\n")
        (self.skill / "SKILL.md").write_text("# demo\n")
        (self.skill / "scripts" / "run.py").write_text("from kitlib import VALUE\nprint(VALUE)\n")

    def test_build_copies_a_self_contained_skill(self):
        paths = package.build(self.root, self.output, True)
        self.assertEqual([p.name for p in paths], ["sw-demo"])
        skill = self.output / "sw-demo"
        self.assertTrue((skill / "scripts" / "kitlib" / "__init__.py").exists())
        self.assertEqual((skill / "LICENSE").read_text(), "MIT\n")
        self.assertTrue((skill / "references" / "safety.md").exists())
        result = subprocess.run(
            [sys.executable, str(skill / "scripts" / "run.py")],
            cwd=self.base,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        self.assertEqual(result.stdout.strip(), "7")

    def test_zip_is_reproducible_and_scoped_to_one_skill(self):
        package.build(self.root, self.output, True)
        other = self.base / "other"
        package.build(self.root, other, True)
        first = self.output / "sw-demo.zip"
        self.assertEqual(first.read_bytes(), (other / first.name).read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertTrue(all(n.startswith("sw-demo/") for n in archive.namelist()))

    def test_build_refuses_existing_output(self):
        package.build(self.root, self.output)
        with self.assertRaises(FileExistsError):
            package.build(self.root, self.output)

    def test_install_creates_correct_relative_symlink_and_rule_copies(self):
        installer.install(self.root, self.target)
        canonical = self.target / ".agents" / "skills" / "sw-demo"
        alias = self.target / ".claude" / "skills" / "sw-demo"
        self.assertEqual(alias.resolve(), canonical.resolve())
        self.assertEqual(
            (self.target / "CLAUDE.md").read_bytes(), (self.target / "AGENTS.md").read_bytes()
        )
        self.assertTrue((self.target / ".github" / "copilot-instructions.md").exists())

    def test_install_copy_mode_and_preserved_rules(self):
        self.target.mkdir()
        (self.target / "AGENTS.md").write_text("# Existing\n")
        report = installer.install(self.root, self.target, copy_mirror=True)
        self.assertTrue(report["preserved"])
        alias = self.target / ".claude" / "skills" / "sw-demo"
        self.assertTrue(alias.is_dir())
        self.assertFalse(alias.is_symlink())
        self.assertEqual((self.target / "GEMINI.md").read_text(), "# Existing\n")

    def test_collision_is_rejected_before_any_skill_is_written(self):
        collision = self.target / ".claude" / "skills" / "sw-demo"
        collision.mkdir(parents=True)
        (collision / "keep").write_text("important")
        with self.assertRaises(FileExistsError):
            installer.install(self.root, self.target)
        self.assertFalse((self.target / ".agents").exists())
        self.assertEqual((collision / "keep").read_text(), "important")

    def test_zip_contains_one_self_contained_skill(self):
        package.build(self.root, self.output, True)
        with zipfile.ZipFile(self.output / "sw-demo.zip") as archive:
            names = set(archive.namelist())
        required = {
            "sw-demo/SKILL.md",
            "sw-demo/LICENSE",
            "sw-demo/scripts/kitlib/__init__.py",
            "sw-demo/references/safety.md",
        }
        self.assertTrue(required <= names)
        self.assertTrue(all(name.startswith("sw-demo/") for name in names))

    def test_runtime_help_from_an_unrelated_cwd(self):
        package.build(self.root, self.output)
        script = self.output / "sw-demo" / "scripts" / "run.py"
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=self.base,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "7")


if __name__ == "__main__":
    unittest.main()
