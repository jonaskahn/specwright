"""Debate record check (sw-craft) and change merge checks (sw-craft)."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "sw-craft" / "scripts"))

import debate  # noqa: E402

STORY = (
    "---\nid: FEAT-001\ntype: feature\nstatus: in-review\n---\n\n## Goal\n\nAs a user, I want x.\n"
)


class Debate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.story = self.base / "features/FEAT-001/FEAT-001.story.md"
        self.story.parent.mkdir(parents=True)
        self.story.write_text(STORY)
        debate.start(self.base, "FEAT-001", "subagent")
        self.record = self.base / "features/FEAT-001/review" / "FEAT-001.debate.md"

    def tearDown(self):
        self.tmp.cleanup()

    def add(self, rows):
        t = self.record.read_text()
        t = t.replace(
            "| --- | --- | --- | --- | --- | --- | --- |\n",
            "| --- | --- | --- | --- | --- | --- | --- |\n" + rows,
        )
        self.record.write_text(t)

    def test_accepted_fix_needs_seal(self):
        self.add("| F-1 | builder | major | x | AC-001-1 | accepted | added AC-001-3 |\n")
        self.story.write_text(STORY + "\nmore\n")
        self.assertIn("seal", " ".join(debate.check(self.base, "FEAT-001")["findings"]))
        debate.seal(self.base, "FEAT-001")
        self.assertTrue(debate.check(self.base, "FEAT-001")["finalizable"])

    def test_open_blocker_blocks_and_held_major_is_a_dispute(self):
        self.add(
            "| F-1 | critic | blocker | y | AC-001-1 | open | Q-001 |\n"
            "| F-2 | tester | major | z | AC-001-2 | rebutted | BR-001 says so · holds |\n"
        )
        r = debate.check(self.base, "FEAT-001")
        self.assertFalse(r["finalizable"])
        self.assertEqual(len(r["disputes"]), 2)

    def test_evidence_and_response_required(self):
        self.add("| F-1 | critic | minor | vague | none | rebutted | no |\n")
        text = " ".join(debate.check(self.base, "FEAT-001")["findings"])
        self.assertIn("no evidence", text)
        self.assertIn("rebuttal needs evidence", text)

    def test_changed_draft_opens_new_round(self):
        debate.seal(self.base, "FEAT-001")
        self.story.write_text(STORY + "\nchanged\n")
        self.assertFalse(debate.check(self.base, "FEAT-001")["finalizable"])
        debate.start(self.base, "FEAT-001", "subagent")
        self.assertIn("Earlier findings", self.record.read_text())
        self.assertEqual(
            debate.check(self.base, "FEAT-001")["findings"],
            ["no findings and no round recorded; run the reviewers"],
        )


@unittest.skipUnless(shutil.which("git"), "git needed")
class MergeCli(unittest.TestCase):
    def test_help_runs(self):
        done = subprocess.run(
            [sys.executable, str(ROOT / "skills/sw-craft/scripts/merge.py"), "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(done.returncode, 0)
        self.assertIn("finish", done.stdout)


if __name__ == "__main__":
    unittest.main()
