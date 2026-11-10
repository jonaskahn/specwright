import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from kitlib import frontmatter, hashing, rtm, workspace

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills/_shared/scripts/status.py"
SPEC = importlib.util.spec_from_file_location("refund_status", SCRIPT)
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "refund"
        shutil.copytree(ROOT / "fixtures/refund/after-spec", self.root)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=15
        )

    def test_refund_report_contains_expected_hand_off_without_writes(self):
        before = {
            str(p.relative_to(self.root)): p.read_bytes()
            for p in self.root.rglob("*")
            if p.is_file()
        }
        report = status.build_report(self.root, today=date(2026, 11, 10))
        text = status.render(report)
        self.assertIn(
            "REF:FEAT-001 | in-review | lint review: pass | Jira: — | Q-001 open | "
            "next: sw-review (PO)",
            text,
        )
        self.assertEqual(report["features"][1]["idle_days"], 14)
        self.assertTrue(report["features"][1]["idle"])
        self.assertEqual(report["features"][0]["snapshot_age_days"], "unknown")
        self.assertEqual(report["features"][1]["open_changes"], ["REF:CR-001"])
        self.assertEqual(
            before,
            {
                str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*")
                if p.is_file()
            },
        )

    def test_signoff_is_recomputed_from_body_hash_and_identity_is_excluded(self):
        path = self.root / "02-drafts/FEAT-001.story.md"
        digest = hashing.draft_hash(path.read_text())
        path.write_text(
            frontmatter.update(
                path.read_text(),
                {"signoffs": [f"PO | Lan | sha256:{digest[7:19]} | https://example.test/review/1"]},
            )
        )
        self.assertEqual(status.build_report(self.root)["features"][0]["signoff"], "fresh")
        path.write_text(
            path.read_text().replace("identity FEAT-001.", "identity FEAT-001; checked.")
        )
        self.assertEqual(status.build_report(self.root)["features"][0]["signoff"], "fresh")
        path.write_text(path.read_text().replace("50 USD", "60 USD"))
        self.assertEqual(status.build_report(self.root)["features"][0]["signoff"], "stale")

    def test_json_optional_save_and_missing_lint_unknown(self):
        result = self.run_cli("--cwd", str(self.root), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["features"]), 2)
        self.assertFalse((self.root / "_meta/status.md").exists())
        (self.root / "_meta/lint-report.md").unlink()
        self.assertEqual(status.build_report(self.root)["features"][0]["lint"], "unknown")
        result = self.run_cli("--cwd", str(self.root), "--save")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / "_meta/status.md").exists())
        self.assertEqual(self.run_cli("--help").returncode, 0)
        self.assertEqual(self.run_cli("--cwd", self.temp.name).returncode, 2)
        self.assertEqual(self.run_cli("--scope", "BAD", "--cwd", str(self.root)).returncode, 2)

    def test_ready_for_dev_first_drift_and_snapshot_age(self):
        path = self.root / "02-drafts/FEAT-002.story.md"
        path.write_text(frontmatter.update(path.read_text(), {"status": "ready-for-dev"}))
        rtm.set_cell(self.root, "REF", "FEAT-002", "Drift", "content-edited", "sw-publish")
        snap = self.root / "snapshots/jira/PROJ-14.md"
        snap.write_text(
            frontmatter.render(
                {"id": "SRC-0001", "type": "snapshot", "fetched_at": "2026-11-01T03:12:00Z"},
                "# Imported story\n",
            )
        )
        rtm.registry_upsert(
            self.root / "_meta/id-registry.md",
            "REF:FEAT-002",
            {"Last snapshot": "snapshots/jira/PROJ-14.md"},
            "sw-publish",
        )
        item = status.build_report(self.root, today=date(2026, 11, 10))["features"][0]
        self.assertEqual(item["id"], "REF:FEAT-002")
        self.assertEqual(item["snapshot_age_days"], 9)
        self.assertEqual(item["next"], "review")
        self.assertEqual(status.age_days("invalid", date(2026, 11, 10)), "unknown")

    def test_all_program_scopes_without_questions_and_save_refusal(self):
        root = Path(self.temp.name) / "program"
        for scope in ("REF", "ORD"):
            workspace.init(root, "program", scope, scope)
            path = root / "projects" / scope / "02-drafts/FEAT-001.story.md"
            path.write_text(frontmatter.render({"id": "FEAT-001", "type": "feature"}, "# Story\n"))
        result = self.run_cli("--cwd", str(root), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["features"]), 2)
        self.assertEqual(result.stderr, "")
        result = self.run_cli("--cwd", str(root), "--save")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((root / "projects/REF/_meta/status.md").exists())

    def test_malformed_data_and_path_escape_fail_safely(self):
        rtm.registry_upsert(
            self.root / "_meta/id-registry.md",
            "REF:FEAT-001",
            {"Last snapshot": "../../outside.md"},
            "sw-publish",
        )
        result = self.run_cli("--cwd", str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertIn("escapes", result.stderr)
        self.assertFalse((self.root / "_meta/status.md").exists())
        (self.root / "_meta/id-registry.md").write_text("bad table\n")
        self.assertEqual(self.run_cli("--cwd", str(self.root)).returncode, 2)
