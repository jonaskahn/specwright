"""One batch imports many sources, links parents, reconciles counts and records what happened."""

import json
import subprocess
import sys
from pathlib import Path

from kitlib import frontmatter, graph, graph_query, ids, miniyaml, rtm, schema
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parents[2] / "skills/sw-ingest/scripts/bulk_import.py"
ELIGIBLE = (
    "# Eligibility\n\nAn order is eligible when it was delivered within 14 days and the goods are "
    "unused, unopened and returned in their original packaging by the customer.\n"
)
PAYOUT = (
    "# Payout\n\nA payout is released after the warehouse confirms the return and the finance team "
    "has approved the amount for the original payment method of the customer.\n"
)
PAGES = {
    "home.md": "# Refund space\n\n- [Eligibility](https://w.test/2)\n",
    "eligibility.md": ELIGIBLE,
    "payout.md": PAYOUT,
}
LIST = (
    "path\ttitle\tsource\tsource_version\tremote_id\tparent_id\ttracker_key\turl\n"
    "payout.md\tPayout\twiki:30\tv4\t30\t10\t\thttps://w.test/30\n"
    "eligibility.md\tEligibility\twiki:20\tv2\t20\t10\tWIKI-20\thttps://w.test/20\n"
    "home.md\tRefund space\twiki:10\tv9\t10\t\t\thttps://w.test/10\n"
)


class BulkImportTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.pages = self.root / "export"
        self.pages.mkdir()
        for name, text in PAGES.items():
            (self.pages / name).write_text(text)
        (self.pages / "list.tsv").write_text(LIST)

    def run_batch(self, *args, batch="b1", listed=True):
        source = (
            ["--list-file", str(self.pages / "list.tsv")]
            if listed
            else ["--input-dir", str(self.pages)]
        )
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--batch-id",
                batch,
                *source,
                *args,
                "--cwd",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

    def batch_manifest(self, batch="b1"):
        return json.loads((self.base / f"00-inbox/imports/{batch}/manifest.json").read_text())

    def snapshot(self, ident):
        return frontmatter.parse(ids.find_record(self.base / "00-inbox", ident).read_text()).fm

    def test_a_batch_creates_snapshots_parents_first_and_writes_a_manifest(self):
        result = self.run_batch("--expected", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.batch_manifest()
        self.assertEqual(
            (data["expected_count"], data["received_count"], data["counts"], data["counts_match"]),
            (3, 3, {"created": 3}, True),
        )
        order = [i["remote_id"] for i in data["items"]]
        self.assertEqual(order[0], "10")  # the parent page comes first
        by_remote = {i["remote_id"]: i["src_id"] for i in data["items"]}
        child = self.snapshot(by_remote["20"])
        self.assertEqual(child["source_parent"], by_remote["10"])
        self.assertEqual(child["source_version"], "v2")
        self.assertEqual(child["aliases"], ["20", "WIKI-20", "https://w.test/20"])
        self.assertEqual(self.snapshot(by_remote["10"])["content_class"], "index-only")
        self.assertTrue(all(i["exit_code"] == 0 for i in data["items"]))

    def test_registry_and_graph_carry_the_remote_names_and_hierarchy(self):
        self.run_batch()
        table = rtm.read_table(
            self.base / "_meta/id-registry.md", list(schema.REGISTRY_COLUMNS)
        ).table
        refs = sorted(table.value(r[0], "Source ref") for r in table.rows if ":SRC-" in r[0])
        self.assertEqual(refs, ["10", "20", "30"])
        graph.build(self.root, "REF")
        store = graph_query.Store(self.root, "REF")
        self.assertEqual(store.resolve("WIKI-20"), "REF:SRC-0003")
        edges = [e for e in store.edges("out") if e.rel == "source_parent"]
        self.assertEqual(
            sorted((e.src, e.dst) for e in edges),
            [
                ("REF:SRC-0002", "REF:SRC-0001"),
                ("REF:SRC-0003", "REF:SRC-0001"),
            ],
        )

    def test_dry_run_shows_the_plan_and_writes_nothing(self):
        before = sorted(p.name for p in (self.base / "00-inbox").rglob("*"))
        result = self.run_batch("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertTrue(plan["dry_run"])
        self.assertEqual([i["src_id"] for i in plan["items"]], ["SRC-0001", "SRC-0002", "SRC-0003"])
        self.assertEqual(plan["items"][1]["source_version"], "v4")
        self.assertEqual(before, sorted(p.name for p in (self.base / "00-inbox").rglob("*")))

    def test_a_batch_over_the_limit_needs_the_typed_count(self):
        path = self.base / "project.yaml"
        data = miniyaml.loads(path.read_text())
        data["limits"]["max_pages"] = 2
        path.write_text(miniyaml.dumps(data))
        refused = self.run_batch()
        self.assertEqual(refused.returncode, 3)
        self.assertIn("--confirm-over-limit 3", refused.stderr)
        self.assertFalse((self.base / "00-inbox/imports/b1").exists())
        wrong = self.run_batch("--confirm-over-limit", "2")
        self.assertEqual(wrong.returncode, 3)
        self.assertEqual(self.run_batch("--confirm-over-limit", "3").returncode, 0)

    def test_expected_and_received_counts_are_reconciled(self):
        result = self.run_batch("--expected", "4")
        self.assertEqual(result.returncode, 5)
        data = self.batch_manifest()
        self.assertFalse(data["counts_match"])
        self.assertEqual((data["expected_count"], data["received_count"]), (4, 3))

    def test_a_registered_source_supplies_the_expected_count(self):
        from kitlib import workspace

        workspace.add_source(self.root, "REF", "wiki", "confluence", "SPACE/Home", "2026-11-01", 5)
        result = self.run_batch("--source-id", "wiki")
        self.assertEqual(result.returncode, 5)
        self.assertEqual(self.batch_manifest()["source"]["system"], "confluence")
        unknown = self.run_batch("--source-id", "nope", batch="b2")
        self.assertEqual(unknown.returncode, 2)

    def test_a_refused_item_does_not_stop_the_rest_and_is_reported(self):
        (self.pages / "payout.md").write_text(
            "# Payout\n\nContact finance@example.test for help.\n"
        )
        result = self.run_batch()
        self.assertEqual(result.returncode, 3)
        counts = self.batch_manifest()["counts"]
        self.assertEqual(counts, {"created": 2, "refused": 1})

    def test_reimport_is_idempotent_and_batch_ids_are_not_reused(self):
        self.run_batch()
        again = self.run_batch(batch="b2")
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual(self.batch_manifest("b2")["counts"], {"duplicate": 3})
        self.assertEqual(self.run_batch(batch="b2").returncode, 2)
        self.assertEqual(len(list((self.base / "00-inbox").glob("SRC-*.md"))), 3)

    def test_a_missing_file_is_an_error_item(self):
        (self.pages / "payout.md").unlink()
        result = self.run_batch()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.batch_manifest()["counts"], {"created": 2, "error": 1})

    def test_a_folder_imports_every_file(self):
        (self.pages / "list.tsv").unlink()
        result = self.run_batch(listed=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.batch_manifest()["received_count"], 3)

    def test_invalid_requests_exit_two(self):
        bad = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--batch-id",
                "Bad Id",
                "--list-file",
                "x",
                "--cwd",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(bad.returncode, 2)
        none = subprocess.run(
            [sys.executable, str(SCRIPT), "--batch-id", "ok", "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(none.returncode, 2)
