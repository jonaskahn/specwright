"""A legacy register becomes reserved features, one brief per group and a first question."""

import json
import subprocess
import sys
from pathlib import Path

from kitlib import baseline, frontmatter, graph, graph_query, invest, recordops, workspace
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parents[2] / "skills/sw-shape/scripts/baseline.py"
RECORD = Path(__file__).resolve().parents[2] / "skills/_shared/scripts/record.py"
REGISTER = (
    "ID,Name,Module,Page\n"
    "LEG-100,Request a refund,Refunds,page-1\n"
    "LEG-101,Decide a refund,Refunds,page-2\n"
    "LEG-200,Issue a payout,Payments,page-3\n"
)


class BaselineTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.file = self.root / "legacy.csv"
        self.file.write_text(REGISTER)

    def run_cli(self, script, *args):
        return subprocess.run(
            [sys.executable, str(script), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=90,
        )

    def baseline_cli(self, *args):
        return self.run_cli(SCRIPT, *args)

    def register(self):
        result = self.baseline_cli("import-register", str(self.file))
        self.assertEqual(result.returncode, 0, result.stderr)

    # ---- register

    def test_synonym_columns_are_normalized_and_written_once(self):
        dry = self.baseline_cli("import-register", str(self.file), "--dry-run")
        self.assertIn("3 legacy item(s) in 2 group(s)", dry.stdout)
        self.assertFalse((self.base / baseline.REGISTER).exists())
        self.register()
        text = (self.base / baseline.REGISTER).read_text()
        self.assertEqual(text.splitlines()[0], "legacy_id\ttitle\tgroup\tsource_ref")
        self.assertIn("LEG-100\tRequest a refund\tRefunds\tpage-1", text)
        again = self.baseline_cli("import-register", str(self.file))
        self.assertEqual(again.returncode, 2)
        self.assertIn("--replace", again.stderr)
        self.assertEqual(
            self.baseline_cli("import-register", str(self.file), "--replace").returncode, 0
        )

    def test_a_bad_register_is_refused_with_the_row(self):
        for text, expected in (
            ("ID,Name\nLEG-1,One\nLEG-1,Two\n", "appears twice"),
            ("Name\nOne\n", "'legacy_id' column"),
            ("ID,Name\nLEG-1,\n", "required"),
            ("ID,Name\n", "at least one item"),
        ):
            with self.assertRaisesRegex(baseline.BaselineError, expected):
                baseline.parse_register(text)

    def test_a_registered_source_pattern_checks_the_legacy_ids(self):
        workspace.add_source(
            self.root, "REF", "legacy", "excel", "reqs.xlsx", "2026-11-01", 3, r"LEG-\d{3}"
        )
        self.assertEqual(
            self.baseline_cli(
                "import-register", str(self.file), "--source-id", "legacy"
            ).returncode,
            0,
        )
        self.file.write_text(REGISTER.replace("LEG-200", "OLD-200"))
        bad = self.baseline_cli(
            "import-register", str(self.file), "--source-id", "legacy", "--replace"
        )
        self.assertEqual(bad.returncode, 2)
        self.assertIn("does not match", bad.stderr)

    # ---- grouping and reservation

    def test_grouping_lists_items_without_a_feature_and_writes_a_proposal(self):
        self.register()
        out = self.baseline_cli("propose-grouping")
        self.assertIn("Refunds: 2 item(s), 2 without a feature", out.stdout)
        self.assertIn("Payments: 1 item(s), 1 without a feature", out.stdout)
        proposal = (self.base / baseline.PROPOSAL).read_text()
        self.assertIn("Refunds\tLEG-101\tDecide a refund", proposal)

    def test_reserving_keeps_each_legacy_id_as_an_alias_and_is_idempotent(self):
        self.register()
        dry = self.baseline_cli("reserve", "--group", "Refunds", "--dry-run")
        self.assertIn("reserve REF:FEAT-002 'Request a refund'", dry.stdout)
        self.assertEqual(self.baseline_cli("reserve", "--group", "Refunds").returncode, 0)
        graph.build(self.root, "REF")
        store = graph_query.Store(self.root, "REF")
        self.assertEqual(store.resolve("LEG-100"), "REF:FEAT-002")
        self.assertEqual(store.resolve("LEG-101"), "REF:FEAT-003")
        again = self.baseline_cli("reserve", "--group", "Refunds")
        self.assertIn("already has a feature", again.stdout)
        self.assertEqual(self.baseline_cli("reserve", "--group", "Nope").returncode, 2)

    # ---- brief

    def test_a_brief_needs_reservations_then_carries_the_table_and_the_first_question(self):
        self.register()
        early = self.baseline_cli("brief", "--group", "Refunds")
        self.assertEqual(early.returncode, 2)
        self.assertIn("reserve this group first", early.stderr)
        (self.base / "00-inbox/SRC-0001.md").write_text(
            frontmatter.render(
                {
                    "id": "SRC-0001",
                    "type": "snapshot",
                    "status": "raw",
                    "title": "Policy",
                    "aliases": ["page-1"],
                    "remote_id": "page-1",
                },
                "Refund policy text.\n",
            )
        )
        self.baseline_cli("reserve", "--group", "Refunds")
        done = self.baseline_cli("brief", "--group", "Refunds")
        self.assertEqual(done.returncode, 0, done.stderr)
        brief = self.base / "01-analysis/ideas/IDEA-baseline-refunds.md"
        parsed = frontmatter.parse(brief.read_text())
        self.assertEqual(parsed.fm["sources"], ["SRC-0001"])
        rows, problems = invest.parse(parsed.body)
        self.assertEqual(problems, [])
        self.assertEqual(
            [r["Feature"] for r in rows],
            ["Request a refund (LEG-100)", "Decide a refund (LEG-101)"],
        )
        self.assertTrue(all(r["I"] == "unknown" for r in rows))
        self.assertIn("| LEG-100 | FEAT-002 | Request a refund | page-1 |", parsed.body)
        question = frontmatter.parse(next((self.base / "records").glob("Q-001--*.md")).read_text())
        self.assertEqual(question.fm["status"], "proposed")
        self.assertEqual(question.fm["affects"], ["FEAT-002", "FEAT-003"])
        graph.build(self.root, "REF")
        rows = {r["id"]: r for r in graph_query.board(graph_query.Store(self.root, "REF"))}
        self.assertEqual(rows["REF:FEAT-002"]["blocked_by_q"], ["REF:Q-001"])
        again = self.baseline_cli("brief", "--group", "Refunds")
        self.assertEqual(again.returncode, 2)
        self.assertIn("already exists", again.stderr)

    def test_the_generated_brief_passes_the_leakage_scan(self):
        self.register()
        self.baseline_cli("reserve", "--group", "Refunds")
        self.baseline_cli("brief", "--group", "Refunds")
        leakage = SCRIPT.parent / "leakage.py"
        result = subprocess.run(
            [
                sys.executable,
                str(leakage),
                str(self.base / "01-analysis/ideas/IDEA-baseline-refunds.md"),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("not scanned", result.stdout)

    # ---- the split decision and the crosswalk

    def test_the_accepted_split_takes_reserved_and_new_items_from_the_register(self):
        self.register()
        self.baseline_cli("reserve", "--group", "Refunds")
        result = self.run_cli(
            RECORD,
            "accept-split",
            "--from-register",
            "Refunds",
            "--new-epic",
            "Refund journeys",
            "--decided-by-role",
            "PO",
            "--decided-by-name",
            "Lan",
            "--evidence-kind",
            "url",
            "--evidence-ref",
            "https://example.test/minutes/3",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        made = json.loads(result.stdout)["made"]
        self.assertEqual(made, ["EPIC-001", "DEC-001"])  # both features were already reserved
        store = graph_query.Store(self.root, "REF")
        members = sorted(
            e.src for e in store.edges_for({"REF:EPIC-001"}, "in") if e.rel == "member_of"
        )
        self.assertEqual(members, ["REF:FEAT-002", "REF:FEAT-003"])

    def test_the_crosswalk_matches_registered_items_and_lists_the_rest(self):
        self.register()
        (self.base / "00-inbox/SRC-0001.md").write_text(
            frontmatter.render(
                {
                    "id": "SRC-0001",
                    "type": "snapshot",
                    "status": "raw",
                    "title": "Policy",
                    "aliases": ["page-1"],
                    "remote_id": "page-1",
                },
                "Refund policy text.\n",
            )
        )
        self.baseline_cli("reserve", "--group", "Refunds")
        lines = (self.base / "_meta/CROSSWALK.tsv").read_text().splitlines()
        head = lines[1][2:].split("\t")
        rows = {
            r["legacy_id"]: r
            for r in (dict(zip(head, ln.split("\t"), strict=False)) for ln in lines[2:])
        }
        self.assertEqual(rows["LEG-100"]["match"], "matched")
        self.assertEqual(rows["LEG-101"]["match"], "no-source")
        self.assertEqual(rows["LEG-200"]["match"], "no-feature")
        self.assertEqual(recordops.RecordError.__name__, "RecordError")
