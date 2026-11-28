"""Pre-ship verification rows (kitlib.analysis) and Jira status sync planning (sw-ship)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))
sys.path.insert(0, str(ROOT / "skills" / "sw-ship" / "scripts"))

# kitlib must be imported before status_sync: status_sync prepends its own _shared on import.
from kitlib import analysis  # noqa: E402,I001

import status_sync  # noqa: E402

STORY = (
    "---\nid: FEAT-003\ntype: feature\nstatus: {status}\n{extra}---\n\n"
    "## Acceptance criteria\n\n"
    "### AC-003-1 — Refuse after 10 days\n\n- **Given** a\n- **When** b\n- **Then** c\n\n"
    "### AC-003-2 — Save within 10 days\n\n- **Given** a\n- **When** b\n- **Then** c\n"
)
REGISTRY = (
    "| Spec ID | Kind | Jira key | State |\n|---|---|---|---|\n| S:FEAT-003 | story | S-14 | x |\n"
)


class Workspace(unittest.TestCase):
    @staticmethod
    def put(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        for d in ("features/FEAT-001", "01-analysis/as-is", ".metadata", "code/src"):
            (self.base / d).mkdir(parents=True)
        (self.base / "code/src/S.java").write_text("int W = 10;\n")
        (self.base / ".metadata/id-registry.md").write_text(REGISTRY)

    def tearDown(self):
        self.tmp.cleanup()

    def story(self, status="ready-to-publish", extra=""):
        self.put(
            self.base / "features/FEAT-003/FEAT-003.story.md",
            STORY.format(status=status, extra=extra),
        )


class Verify(Workspace):
    def table(self, rows):
        path = self.base / "01-analysis/as-is/FEAT-003.verify.analysis.md"
        path.write_text(
            "---\nkind: analysis\nverifies: FEAT-003\ntarget: FEAT-003\nstatus: draft\n---\n\n"
            "## Criteria\n\n| # | Criterion | Intended | Actual | Status | Confidence | Notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n" + rows + "\n## Conflicts\n\nNone\n"
        )
        return analysis.check(path, {"code": self.base / "code"})

    def test_every_ac_needs_a_row_and_done(self):
        self.story()
        c = analysis.cite({"code": self.base / "code"}, "code/src/S.java", 1)
        r = self.table(f"| AC-003-1 | x | AC-003-1 | {c} | done | high | |\n")
        self.assertFalse(r["verified"])
        self.assertIn("AC-003-2: no verification row", " ".join(r["findings"]))
        r = self.table(
            f"| AC-003-1 | x | AC-003-1 | {c} | done | high | |\n"
            f"| AC-003-2 | y | AC-003-2 | {c} | done | high | |\n"
        )
        self.assertTrue(r["verified"])
        self.assertIn("merge.py ship", r["recommend"])


class Sync(Workspace):
    def manifest(self, on=True):
        return {"jira": {"site": "https://x.atlassian.net", "status_sync": on}}

    def test_local_states(self):
        self.story(status="in-review")
        self.assertEqual(status_sync.local_state(self.base, "FEAT-003"), "review")
        self.story(extra="shipped: [code@abc]\n")
        self.assertEqual(status_sync.local_state(self.base, "FEAT-003"), "shipped")
        self.story(extra="origin: as-is\n")
        self.assertEqual(status_sync.local_state(self.base, "FEAT-003"), "shipped")

    def test_plan_needs_opt_in_and_remote(self):
        self.story(extra="shipped: [code@abc]\n")
        r = status_sync.plan(self.base, "S", self.manifest(False), [], {})
        self.assertEqual(len(r["blocked"]), 2)
        self.assertIsNone(r["token"])
        r = status_sync.plan(self.base, "S", self.manifest(), [], {"S-14": "In Progress"})
        self.assertEqual(r["transitions"][0]["target"], "Done")
        self.assertTrue(r["token"].startswith("SYNC S "))

    def test_jira_ahead_is_drift_not_pulled(self):
        self.story()
        r = status_sync.plan(self.base, "S", self.manifest(), [], {"S-14": "Done"})
        self.assertEqual(r["drift"][0]["key"], "S-14")
        self.assertEqual(r["transitions"], [])


if __name__ == "__main__":
    unittest.main()
