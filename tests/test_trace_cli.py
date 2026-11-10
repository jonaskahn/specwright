import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/_shared/scripts/trace.py"


class TraceCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "refund"
        shutil.copytree(ROOT / "fixtures/refund/after-spec", self.root)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=15
        )

    def test_findings_and_rebuild_exit_one(self):
        for command in ("check", "rebuild"):
            result = self.run_cli(command, "--cwd", str(self.root))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("REF:FEAT-002 orphan: no BO (L-005)", result.stdout)

    def test_set_enforces_owner_and_impact_json(self):
        args = (
            "set",
            "FEAT-001",
            "--cwd",
            str(self.root),
            "--column",
            "Jira",
            "--value",
            "PROJ-14",
        )
        self.assertEqual(self.run_cli(*args, "--as", "sw-spec").returncode, 4)
        self.assertEqual(self.run_cli(*args, "--as", "sw-publish").returncode, 0)
        result = self.run_cli("impact", "BO-001", "--cwd", str(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["features"], ["REF:FEAT-001"])

    def test_usage_missing_workspace_and_clean_exit(self):
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertEqual(self.run_cli("set").returncode, 2)
        self.assertEqual(self.run_cli("check", "--cwd", self.temp.name).returncode, 2)
        from kitlib import frontmatter

        path = self.root / "02-drafts/FEAT-002.story.md"
        path.write_text(frontmatter.update(path.read_text(), {"bo": ["BO-001"]}))
        self.assertEqual(self.run_cli("check", "--cwd", str(self.root)).returncode, 0)
        self.assertEqual(self.run_cli("impact", "BO-099", "--cwd", str(self.root)).returncode, 2)
