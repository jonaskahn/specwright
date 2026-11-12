import importlib.util
import json
import re
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
        (self.root / "skills/_shared/scripts/kitlib").mkdir(parents=True)
        (self.root / "skills/_shared/scripts/kitlib/__init__.py").write_text("VALUE = 7\n")
        (self.root / "skills/_shared/scripts/graph.py").write_text("print('graph')\n")
        (self.root / "skills/_shared/references").mkdir(parents=True)
        (self.root / "skills/_shared/references/safety.md").write_text("shared\n")
        (self.root / "skills/_shared/bundle-map.json").write_text(
            json.dumps(
                {
                    "limits": {"max_files": 200},
                    "capabilities": {},
                    "skills": {
                        "sw-start": {
                            "capabilities": [],
                            "shared": ["references/safety.md", "scripts/kitlib/__init__.py"],
                        }
                    },
                }
            )
        )
        (self.root / "LICENSE").write_text("MIT\n")
        (self.root / "AGENTS.md").write_text("# Rules\n")
        self.skill = self.root / "skills" / "sw-start"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "references").mkdir()
        (self.skill / "references" / "safety.md").write_text(
            "Read ../_shared/references/safety.md.\n"
        )
        (self.skill / "LICENSE").write_text("MIT\n")
        (self.skill / "SKILL.md").write_text("# demo\n")
        (self.skill / "scripts" / "run.py").write_text(
            "import sys\nfrom pathlib import Path\n"
            "_here = Path(__file__).resolve().parent\n"
            "_shared = _here.parent / '_shared' / 'scripts'\n"
            "sys.path.insert(0, str(_shared))\n"
            "from kitlib import VALUE\nprint(VALUE)\n"
        )

    def test_build_copies_a_self_contained_skill(self):
        paths = package.build(self.root, self.output, True)
        self.assertEqual([p.name for p in paths], ["sw-start"])
        skill = self.output / "sw-start"
        self.assertTrue((skill / "_shared" / "scripts" / "kitlib" / "__init__.py").exists())
        self.assertEqual((skill / "LICENSE").read_text(), "MIT\n")
        self.assertTrue((skill / "_shared" / "references" / "safety.md").exists())
        self.assertFalse((skill / "_shared" / "scripts" / "graph.py").exists())
        self.assertIn("_shared/references/safety.md", (skill / "references/safety.md").read_text())
        self.assertNotIn("../_shared", (skill / "references/safety.md").read_text())
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
        first = self.output / "sw-start.zip"
        self.assertEqual(first.read_bytes(), (other / first.name).read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertTrue(all(n.startswith("sw-start/") for n in archive.namelist()))

    def test_build_refuses_existing_output(self):
        package.build(self.root, self.output)
        with self.assertRaises(FileExistsError):
            package.build(self.root, self.output)

    def test_install_creates_correct_relative_symlink_and_rule_copies(self):
        installer.install(self.root, self.target)
        canonical = self.target / ".agents" / "skills" / "sw-start"
        alias = self.target / ".claude" / "skills" / "sw-start"
        self.assertEqual(alias.resolve(), canonical.resolve())
        self.assertIn("@AGENTS.md", (self.target / "CLAUDE.md").read_text())
        self.assertNotEqual(
            (self.target / "CLAUDE.md").read_bytes(), (self.target / "AGENTS.md").read_bytes()
        )
        self.assertTrue((self.target / ".github" / "copilot-instructions.md").exists())

    def test_install_copy_mode_and_preserved_rules(self):
        self.target.mkdir()
        (self.target / "AGENTS.md").write_text("# Existing\n")
        report = installer.install(self.root, self.target, copy_mirror=True)
        self.assertTrue(report["preserved"])
        alias = self.target / ".claude" / "skills" / "sw-start"
        self.assertTrue(alias.is_dir())
        self.assertFalse(alias.is_symlink())
        self.assertIn("@AGENTS.md", (self.target / "GEMINI.md").read_text())

    def test_collision_is_rejected_before_any_skill_is_written(self):
        collision = self.target / ".claude" / "skills" / "sw-start"
        collision.mkdir(parents=True)
        (collision / "keep").write_text("important")
        with self.assertRaises(FileExistsError):
            installer.install(self.root, self.target)
        self.assertFalse((self.target / ".agents").exists())
        self.assertEqual((collision / "keep").read_text(), "important")

    def test_zip_contains_one_self_contained_skill(self):
        package.build(self.root, self.output, True)
        with zipfile.ZipFile(self.output / "sw-start.zip") as archive:
            names = set(archive.namelist())
        required = {
            "sw-start/SKILL.md",
            "sw-start/LICENSE",
            "sw-start/_shared/scripts/kitlib/__init__.py",
            "sw-start/_shared/references/safety.md",
        }
        self.assertTrue(required <= names)
        self.assertTrue(all(name.startswith("sw-start/") for name in names))
        self.assertFalse(any(re.search(r"(^|/)\.\./", name) for name in names))


if __name__ == "__main__":
    unittest.main()
