"""The INVEST table has one fixed shape, so totals never count an unknown as a pass."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

from kitlib import frontmatter, invest
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parents[2] / "skills/sw-shape/scripts/invest.py"
HEAD = "| Feature | I | N | V | E | S | T | Reason |\n|---|---|---|---|---|---|---|---|\n"
ROW1 = "| Request a refund | pass | pass | pass | unknown | pass | pass | Delivery-day rule |\n"
ROW2 = "| Decide a refund | Pass | PASS | pass | pass | pass | pass | — |\n"
ROW3 = "| Notify the requester | pass | fail | pass | pass | unknown | pass | Channel set |\n"
TABLE = "## Proposed FEAT split\n\nIntro text.\n\n" + HEAD + ROW1 + ROW2 + ROW3
BRIEF = (
    "---\nid: IDEA-refunds\ntype: idea\ntitle: Refunds\nstatus: draft\naliases: []\n---\n"
    "## Problem\nx\n\n"
)


class InvestParseTests(unittest.TestCase):
    def test_rows_normalize_case_and_keep_reasons(self):
        rows, problems = invest.parse(TABLE)
        self.assertEqual(problems, [])
        self.assertEqual(
            [r["Feature"] for r in rows],
            ["Request a refund", "Decide a refund", "Notify the requester"],
        )
        self.assertEqual(rows[1]["I"], "pass")
        self.assertEqual(rows[0]["Reason"], "Delivery-day rule")

    def test_totals_count_each_letter_and_never_promote_unknown(self):
        rows, _ = invest.parse(TABLE)
        total = invest.totals(rows)
        self.assertEqual(total["I"], {"pass": 3, "fail": 0, "unknown": 0})
        self.assertEqual(total["N"], {"pass": 2, "fail": 1, "unknown": 0})
        self.assertEqual(total["E"], {"pass": 2, "fail": 0, "unknown": 1})
        self.assertEqual(total["S"], {"pass": 2, "fail": 0, "unknown": 1})
        self.assertEqual(invest.row_summary(rows[2]), {"pass": 4, "fail": 1, "unknown": 1})

    def test_format_problems_are_named(self):
        cases = {
            "columns must be": TABLE.replace("| Reason |", "| Why |"),
            "no INVEST table": "## Proposed FEAT split\n\nOnly prose.\n",
            "must be pass, fail or unknown": TABLE.replace(
                "| pass | pass | pass | unknown | pass | pass |",
                "| yes | pass | pass | unknown | pass | pass |",
            ),
            "needs a Reason": TABLE.replace("Delivery-day rule", ""),
            "has no Feature": TABLE.replace("Decide a refund", ""),
        }
        for expected, body in cases.items():
            self.assertIn(expected, " | ".join(invest.parse(body)[1]), expected)

    def test_a_brief_without_the_section_has_no_problems(self):
        self.assertEqual(invest.problems("## Problem\nonly\n"), [])
        self.assertTrue(invest.problems("## Proposed FEAT split\n\ntext\n"))


class InvestBoardTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        (self.base / "01-analysis/ideas/IDEA-refunds.md").write_text(BRIEF + TABLE)
        (self.base / "01-analysis/ideas/IDEA-other.md").write_text(
            BRIEF.replace("refunds", "other") + "## Proposed FEAT split\n\nnot yet\n"
        )
        (self.base / "01-analysis/ideas/IDEA-none.md").write_text(BRIEF.replace("refunds", "none"))

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=30
        )

    def test_the_board_totals_per_brief_and_flags_malformed_ones(self):
        boards = {b["idea"]: b for b in invest.board(self.base)}
        self.assertEqual(sorted(boards), ["IDEA-other", "IDEA-refunds"])
        self.assertEqual(boards["IDEA-refunds"]["rows"], 3)
        self.assertEqual(boards["IDEA-refunds"]["totals"]["N"]["fail"], 1)
        self.assertTrue(boards["IDEA-other"]["problems"])

    def test_cli_check_and_totals(self):
        good = self.base / "01-analysis/ideas/IDEA-refunds.md"
        bad = self.base / "01-analysis/ideas/IDEA-other.md"
        self.assertEqual(self.run_cli("check", str(good)).returncode, 0)
        failed = self.run_cli("check", str(bad))
        self.assertEqual(failed.returncode, 1)
        self.assertIn("no INVEST table", failed.stdout)
        totals = self.run_cli("totals", "--cwd", str(self.root), "--format", "json")
        self.assertEqual(totals.returncode, 1)  # the malformed brief
        self.assertEqual(json.loads(totals.stdout)[1]["rows"], 3)
        self.assertEqual(frontmatter.parse(good.read_text()).fm["id"], "IDEA-refunds")
