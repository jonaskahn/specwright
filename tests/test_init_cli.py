import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import miniyaml, schema, tables

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/sw-init/scripts/workspace.py"


class InitCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=15
        )

    def test_flat_defaults_and_refusal_to_overwrite(self):
        args = (
            "init",
            "--root",
            str(self.root),
            "--mode",
            "flat",
            "--scope",
            "REF",
            "--name",
            "Refunds",
            "--project-key",
            "PROJ",
        )
        self.assertEqual(self.run_cli(*args).returncode, 0)
        manifest = miniyaml.loads((self.root / "project.yaml").read_text())
        self.assertFalse(manifest["publish"]["transitions"])
        self.assertTrue(manifest["publish"]["sandbox"])
        for folder in schema.SCOPE_DIRS:
            self.assertTrue((self.root / folder).is_dir())
        self.assertEqual(
            tables.parse((self.root / "_meta/id-registry.md").read_text()).table.rows, []
        )
        before = (self.root / "project.yaml").read_bytes()
        self.assertEqual(self.run_cli(*args).returncode, 2)
        self.assertEqual(before, (self.root / "project.yaml").read_bytes())
        result = self.run_cli("detect", "--cwd", str(self.root))
        self.assertEqual(json.loads(result.stdout)["scopes"], ["REF"])

    def test_program_scope_choice_and_usage_codes(self):
        for scope in ("REF", "ORD"):
            self.assertEqual(
                self.run_cli(
                    "init",
                    "--root",
                    str(self.root),
                    "--mode",
                    "program",
                    "--scope",
                    scope,
                    "--name",
                    scope,
                ).returncode,
                0,
            )
        result = self.run_cli("resolve", "--cwd", str(self.root), "--write")
        self.assertEqual(result.returncode, 3)
        self.assertIn("ORD", result.stderr)
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertEqual(self.run_cli("init").returncode, 2)
        self.assertEqual(
            self.run_cli(
                "init",
                "--root",
                str(self.root),
                "--mode",
                "flat",
                "--scope",
                "bad",
                "--name",
                "Bad",
            ).returncode,
            2,
        )
