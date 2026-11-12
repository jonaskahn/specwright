"""sw-start routes an existing baseline, ranks ready items as advice and prints a context pack."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import baseline, frontmatter, graph, graph_query, workspace
from tests.test_workflow import WorkflowTestCase

START = Path(__file__).resolve().parents[2] / "skills/sw-start/scripts/start.py"
spec = importlib.util.spec_from_file_location("start_under_test", START)
start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(start)


class BaselineRoutingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        workspace.init(
            self.root,
            "flat",
            "REF",
            "Refunds",
            approvers=[{"role": "PO", "name": "Lan", "account_id": "1"}],
            governance={"signoff": "required"},
        )
        graph.build(self.root, "REF")

    def scope(self):
        graph.build(self.root, "REF")
        return start.report(self.root)["scopes_state"][0]

    def test_a_stale_graph_names_the_command_that_rebuilds_it(self):
        (self.root / "01-analysis/ideas/IDEA-001.md").write_text(
            "---\nid: IDEA-001\ntype: idea\ntitle: Late idea\naliases: []\n"
            "status: draft\n---\n# Late\n"
        )
        item = start.report(self.root)["scopes_state"][0]
        self.assertEqual(item["graph"], "stale")
        self.assertEqual(item["next"][0], "shared graph build")
        self.assertIn("graph.py build --cwd", item["next"][1])
        self.assertIn("--scope REF", item["next"][1])

    def test_a_project_with_nothing_still_starts_at_ingest(self):
        item = self.scope()
        self.assertEqual(item["next"][0], "sw-ingest")
        self.assertIn("no sources", item["next"][1])

    def test_each_baseline_step_names_a_concrete_action(self):
        workspace.add_source(self.root, "REF", "wiki", "confluence", "S/Home", "2026-11-01", 4)
        item = self.scope()
        self.assertEqual(item["next"][0], "sw-ingest")
        self.assertTrue(item["next"][1].startswith("existing baseline"))
        self.assertIn("bulk_import.py", item["action"])
        (self.root / "00-inbox/SRC-0001.md").write_text(
            frontmatter.render({"id": "SRC-0001", "type": "snapshot", "status": "raw"}, "text\n")
        )
        item = self.scope()
        self.assertEqual(item["next"][0], "sw-shape")
        self.assertIn("import-register", item["action"])
        register = self.root / baseline.REGISTER
        register.parent.mkdir(parents=True, exist_ok=True)
        register.write_text("legacy_id\ttitle\tgroup\tsource_ref\nLEG-1\tOne\tG\tp1\n")
        item = self.scope()
        self.assertIn("propose-grouping", item["action"])
        self.assertEqual(item["baseline"]["register_items"], 1)
        self.assertEqual(item["baseline"]["legacy_unmapped"], 1)

    def test_once_a_brief_exists_the_normal_route_takes_over(self):
        workspace.add_source(self.root, "REF", "wiki", "confluence", "S/Home", "2026-11-01", 4)
        (self.root / "01-analysis/ideas/IDEA-x.md").write_text(
            frontmatter.render(
                {"id": "IDEA-x", "type": "idea", "status": "draft", "title": "X", "aliases": []},
                "## Problem\nx\n",
            )
        )
        item = self.scope()
        self.assertEqual(item["next"][0], "sw-shape")
        self.assertFalse(item["next"][1].startswith("existing baseline"))

    def test_missing_approvers_are_the_first_action(self):
        data = (self.root / "project.yaml").read_text()
        self.assertIn("PO", data)
        other = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(other, ignore_errors=True))
        workspace.init(other, "flat", "OTH", "Other", governance={"signoff": "required"})
        graph.build(other, "OTH")
        item = start.report(other)["scopes_state"][0]
        self.assertTrue(item["setup"][0].startswith("approvers:"))
        self.assertIn("approvers add", item["action"])
        self.assertEqual(item["governance"], "required")

    def test_optional_signoff_asks_for_no_approvers(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(other, ignore_errors=True))
        workspace.init(other, "flat", "OTH", "Other")
        graph.build(other, "OTH")
        item = start.report(other)["scopes_state"][0]
        self.assertEqual(item["setup"], [])
        self.assertEqual((item["governance"], item["flow"]), ("optional", "guided"))
        self.assertEqual(item["output_default"], "markdown")


class RankingAndPackTests(WorkflowTestCase):
    def story(self, ident, title, **extra):
        text = self.draft.read_text()
        fm = {"id": ident, "title": title, "aliases": [], "status": "draft"}
        fm.update(extra)
        (self.base / f"02-drafts/{ident}.story.md").write_text(frontmatter.update(text, fm))

    def write(self, rel, fm, body="# Body\n"):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.render(fm, body))

    def setUp(self):
        super().setUp()
        self.story("FEAT-001", "Request a refund")
        self.story("FEAT-002", "Decide a refund")
        self.story("FEAT-003", "Notify the requester", depends_on=["FEAT-002"])
        self.write(
            "records/Q-001.md",
            {
                "id": "Q-001",
                "type": "q",
                "title": "Window?",
                "aliases": [],
                "status": "open",
                "affects": ["FEAT-001"],
            },
        )
        brief = (
            "## Proposed FEAT split\n\n| Feature | I | N | V | E | S | T | Reason |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| Request a refund | pass | pass | pass | pass | pass | pass | — |\n"
            "| Decide a refund | pass | pass | pass | unknown | unknown | pass | Not sized |\n"
            "| Notify the requester | pass | fail | pass | pass | pass | pass | Prescribed |\n"
        )
        self.write(
            "01-analysis/ideas/IDEA-refunds.md",
            {
                "id": "IDEA-refunds",
                "type": "idea",
                "title": "Refunds",
                "aliases": [],
                "status": "draft",
            },
            brief,
        )
        graph.build(self.root, "REF")

    def item(self):
        return start.report(self.root)["scopes_state"][0]

    def test_the_ranking_puts_the_fewest_blockers_first_and_says_why(self):
        ranking = self.item()["ranking"]
        self.assertEqual(
            [r["id"] for r in ranking], ["REF:FEAT-002", "REF:FEAT-001", "REF:FEAT-003"]
        )
        by_id = {r["id"]: r for r in ranking}
        self.assertEqual(
            by_id["REF:FEAT-002"]["reasons"], ["2 unknown INVEST cell(s), including size"]
        )
        self.assertEqual(
            by_id["REF:FEAT-003"]["reasons"], ["1 failed INVEST cell(s)", "waits on FEAT-002"]
        )
        self.assertEqual(by_id["REF:FEAT-001"]["reasons"], ["1 blocking question(s)"])

    def test_several_items_route_to_choose_with_the_ranking_as_advice(self):
        item = self.item()
        self.assertEqual(item["next"][0], "choose item")
        self.assertIn("most ready: REF:FEAT-002", item["next"][1])
        self.assertIn("advice", item["action"])
        self.assertLessEqual(len(item["ranking"]), 3)

    def test_a_context_pack_lists_files_in_reading_order_with_hashes_and_blockers(self):
        self.write(
            "records/DEC-001.md",
            {
                "id": "DEC-001",
                "type": "dec",
                "title": "Window is 14 days",
                "aliases": [],
                "status": "accepted",
                "affects": ["FEAT-001"],
            },
        )
        self.write(
            "00-inbox/SRC-0001.md",
            {
                "id": "SRC-0001",
                "type": "snapshot",
                "title": "Policy",
                "aliases": [],
                "status": "raw",
            },
        )
        self.draft.write_text(frontmatter.update(self.draft.read_text(), {"sources": ["SRC-0001"]}))
        graph.build(self.root, "REF")
        pack = start.report(self.root, "REF:FEAT-001", pack=True)["scopes_state"][0]["pack"]
        roles = [f["role"] for f in pack["files"]]
        self.assertEqual(roles[:3], ["manifest", "read-first", "item"])
        self.assertIn("decision", roles)
        self.assertIn("source", roles)
        self.assertEqual(roles, sorted(roles, key=start.ROLE_ORDER.index))
        self.assertTrue(all(f["hash"] for f in pack["files"]))
        item = next(f for f in pack["files"] if f["role"] == "item")
        self.assertEqual(item["path"], "02-drafts/FEAT-001.story.md")
        self.assertEqual(
            pack["questions"],
            [{"key": "REF:Q-001", "title": "Window?", "blocking": True, "status": "open"}],
        )

    def test_a_pack_needs_a_fresh_graph(self):
        self.draft.write_text(self.draft.read_text() + "\nchanged\n")
        with self.assertRaises(graph_query.QueryError):
            start.report(self.root, "REF:FEAT-001", pack=True)
        result = subprocess.run(
            [
                sys.executable,
                str(START),
                "--cwd",
                str(self.root),
                "--item",
                "REF:FEAT-001",
                "--pack",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 3)

    def test_the_pack_is_printed_by_the_cli(self):
        result = subprocess.run(
            [
                sys.executable,
                str(START),
                "--cwd",
                str(self.root),
                "--item",
                "REF:FEAT-001",
                "--pack",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            json.loads(result.stdout)["scopes_state"][0]["pack"]["item"], "REF:FEAT-001"
        )
