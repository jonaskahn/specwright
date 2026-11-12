"""An installed skill must notice missing, changed or mixed-release shared files."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import guard, schema

ROOT = Path(__file__).resolve().parent.parent
START = ROOT / "skills/sw-start"


def make_skill(base: Path) -> Path:
    skill = base / "sw-demo"
    shared = skill / "_shared"
    (shared / "scripts").mkdir(parents=True)
    (shared / "scripts/graph.py").write_text("print('graph')\n")
    (shared / "scripts/kitlib.py").write_text("VALUE = 1\n")
    files = guard.folder_files(shared)
    (shared / guard.MANIFEST).write_text(guard.manifest_for(files))
    return skill


class GuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.skill = make_skill(Path(tmp.name))
        self.shared = self.skill / "_shared"

    def test_whole_install_passes(self):
        self.assertEqual(guard.check(self.skill), [])

    def test_source_checkout_without_a_local_copy_is_not_checked(self):
        shutil.rmtree(self.shared)
        self.assertEqual(guard.check(self.skill), [])

    def test_missing_file_is_named(self):
        (self.shared / "scripts/graph.py").unlink()
        self.assertEqual(guard.check(self.skill), ["_shared/scripts/graph.py is missing"])

    def test_changed_file_is_named(self):
        (self.shared / "scripts/kitlib.py").write_text("VALUE = 2\n")
        self.assertEqual(
            guard.check(self.skill), ["_shared/scripts/kitlib.py differs from the release"]
        )

    def test_line_endings_do_not_count_as_a_change(self):
        (self.shared / "scripts/graph.py").write_bytes(b"print('graph')\r\n")
        self.assertEqual(guard.check(self.skill), [])

    def test_mixed_versions_are_reported(self):
        path = self.shared / guard.MANIFEST
        data = json.loads(path.read_text())
        data["kit_version"] = "0.0.1"
        path.write_text(json.dumps(data))
        problems = guard.check(self.skill)
        self.assertEqual(len(problems), 1)
        self.assertIn(f"kit 0.0.1 but its code is kit {schema.KIT_VERSION}", problems[0])

    def test_missing_or_broken_manifest_is_reported(self):
        path = self.shared / guard.MANIFEST
        path.write_text("{")
        self.assertEqual(guard.check(self.skill), ["_shared/MANIFEST.json is unreadable"])
        path.unlink()
        self.assertEqual(guard.check(self.skill), ["_shared/MANIFEST.json is missing"])

    def test_message_carries_the_reinstall_command(self):
        text = guard.explain(["_shared/a is missing"])
        self.assertIn("_shared/a is missing", text)
        self.assertIn("npx skills add", text)

    def test_every_source_skill_matches_its_manifest(self):
        for skill in sorted((ROOT / "skills").glob("sw-*")):
            self.assertEqual(guard.check(skill), [], skill.name)


class StartGuardTests(unittest.TestCase):
    def run_start(self, skill: Path, cwd: Path, *args):
        return subprocess.run(
            [sys.executable, str(skill / "scripts/start.py"), "--cwd", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_start_stops_with_a_reinstall_hint_when_a_shared_file_is_gone(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            skill = base / "sw-start"
            shutil.copytree(START, skill)
            (skill / "_shared/scripts/status.py").unlink()
            result = self.run_start(skill, base)
            self.assertEqual(result.returncode, 2)
            self.assertIn("reinstall", result.stderr)
            self.assertIn("status.py", result.stderr)

    def test_start_reports_the_kit_version(self):
        with tempfile.TemporaryDirectory() as raw:
            result = self.run_start(START, Path(raw))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["kit_version"], schema.KIT_VERSION)
