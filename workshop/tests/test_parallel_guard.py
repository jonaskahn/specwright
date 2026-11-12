import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/_shared/scripts/parallel_guard.py"
ALLOW = (
    "FEAT-001=02-drafts/FEAT-001.*,diagrams/FEAT-001-*",
    "FEAT-002=02-drafts/FEAT-002.*,diagrams/FEAT-002-*",
)


class ParallelGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "scope"
        for folder in ("02-drafts", "diagrams", "records", "_meta"):
            (self.root / folder).mkdir(parents=True)
        (self.root / "records/Q-001.md").write_text("question\n", encoding="utf-8")
        (self.root / "_meta/id-registry.md").write_text("registry\n", encoding="utf-8")
        self.before = Path(self.temp.name) / "before.json"
        self.run_cli("snapshot", "--scope-root", str(self.root), "--out", str(self.before))

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=15
        )

    def verify(self, *allow, extra=()):
        flags = [a for item in (allow or ALLOW) for a in ("--allow", item)]
        return self.run_cli(
            "verify", "--scope-root", str(self.root), "--before", str(self.before), *flags, *extra
        )

    def write(self, rel, text="x\n"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_each_worker_in_its_own_files_is_clean(self):
        self.write("02-drafts/FEAT-001.story.md")
        self.write("02-drafts/FEAT-001.card.md")
        self.write("02-drafts/FEAT-002.story.md")
        self.write("diagrams/FEAT-002-flow.json")
        result = self.verify()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("clean", result.stdout)

    def test_write_to_a_shared_file_is_stray(self):
        self.write("02-drafts/FEAT-001.story.md")
        self.write("_meta/id-registry.md", "tampered\n")
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY changed _meta/id-registry.md", result.stdout)

    def test_new_record_and_deletion_are_stray(self):
        self.write("records/Q-002.md")
        (self.root / "records/Q-001.md").unlink()
        result = self.verify("FEAT-001=02-drafts/FEAT-001.*", extra=("--json",))
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["stray"], ["records/Q-001.md", "records/Q-002.md"])
        self.assertEqual(data["changes"]["records/Q-001.md"], "deleted")

    def test_sibling_write_is_attributed_to_the_sibling(self):
        self.write("02-drafts/FEAT-002.story.md")
        result = self.verify("FEAT-001=02-drafts/FEAT-001.*")
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY created 02-drafts/FEAT-002.story.md", result.stdout)

    def test_two_owners_of_one_file_collide(self):
        self.write("02-drafts/FEAT-001.story.md")
        result = self.verify("A=02-drafts/FEAT-001.*", "B=02-drafts/*.story.md")
        self.assertEqual(result.returncode, 1)
        self.assertIn("COLLISION 02-drafts/FEAT-001.story.md: owned by A, B", result.stdout)

    def test_star_does_not_cross_a_folder(self):
        self.write("02-drafts/FEAT-001.assets/extra.md")
        result = self.verify()
        self.assertEqual(result.returncode, 1)
        self.assertIn("STRAY", result.stdout)

    def test_bad_input_exits_two(self):
        self.assertEqual(self.verify("no-equals-sign").returncode, 2)
        self.assertEqual(self.verify("W=../outside").returncode, 2)
        self.assertEqual(self.run_cli("verify", "--scope-root", "/missing").returncode, 2)


if __name__ == "__main__":
    unittest.main()
