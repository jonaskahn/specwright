"""Brownfield context: consent, safe discovery, batches and unaccepted reconciliation."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kitlib import analysis, discovery, frontmatter, workspace
from tests.support import put

REPO = Path(__file__).resolve().parents[2]
ANALYZE = REPO / "skills/sw-craft/scripts/analyze.py"


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve()

    def scan(self, **kwargs):
        return discovery.discover(self.repo, consent=True, **kwargs)

    def init(self):
        workspace.init(self.repo, "flat", "REF", "Refunds")
        return self.repo / ".specwright"

    def test_no_consent_never_reads_or_traverses_repository(self):
        with (
            patch.object(workspace, "find_root", side_effect=AssertionError("read")),
            patch.object(discovery.os, "walk", side_effect=AssertionError("scan")),
        ):
            result = discovery.discover(self.repo)
        self.assertEqual(result["state"], "consent_required")
        self.assertEqual(len(result["options"]), 3)

    def test_pre_setup_discovers_root_docs_and_plans_without_writes(self):
        for rel in (
            "README.md",
            "PLAN.md",
            "docs/architecture.rst",
            "plans/refund.txt",
            "adr/decision.adoc",
        ):
            put(self.repo / rel, "# Refunds\n")
        before = sorted(str(p) for p in self.repo.rglob("*"))
        result = self.scan()
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["writes"], [])
        self.assertEqual(before, sorted(str(p) for p in self.repo.rglob("*")))
        self.assertFalse((self.repo / ".specwright").exists())

    def test_generated_hidden_sensitive_and_unrelated_paths_are_excluded(self):
        for rel in (
            "README.md",
            "node_modules/docs/leak.md",
            ".git/docs/leak.md",
            "dist/docs/leak.md",
            "docs/secrets.md",
            "credentials/plan.md",
            "docs/.env.md",
            "src/unrelated.md",
            "docs/raw/original.md",
        ):
            put(self.repo / rel, "# Text\n")
        self.assertEqual([d["path"] for d in self.scan()["documents"]], ["README.md"])

    def test_symlinks_are_never_followed(self):
        with tempfile.TemporaryDirectory() as external:
            put(Path(external) / "secret.md", "secret")
            (self.repo / "docs").symlink_to(external, target_is_directory=True)
            (self.repo / "README.md").symlink_to(Path(external) / "secret.md")
            self.assertEqual(self.scan()["total"], 0)

    def test_selected_directory_is_not_broadened_to_repository(self):
        self.init()
        put(self.repo / "README.md", "outside selection")
        selected = self.repo / "docs"
        put(selected / "refund.md", "selected")
        result = discovery.discover(selected, consent=True)
        self.assertEqual(result["repository"], str(selected))
        self.assertEqual([d["path"] for d in result["documents"]], ["refund.md"])

    def test_large_files_are_skipped_and_coverage_is_explicit(self):
        put(self.repo / "large.md", "x" * (discovery.MAX_BYTES + 1))
        result = self.scan()
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["coverage"]["max_file_bytes"], discovery.MAX_BYTES)
        self.assertIn("unsupported", result["coverage"]["limitations"])

    def test_safety_budget_is_not_a_false_empty_success(self):
        put(self.repo / "README.md", "x")
        with (
            patch.object(discovery, "MAX_ENTRIES", 0),
            self.assertRaisesRegex(ValueError, "smaller directory"),
        ):
            self.scan()

    def test_unreadable_tree_is_not_reported_as_absent(self):
        def denied(root, **kwargs):
            kwargs["onerror"](PermissionError(13, "denied", str(root / "docs")))
            return iter(())

        with (
            patch.object(discovery.os, "walk", side_effect=denied),
            self.assertRaisesRegex(ValueError, "cannot read"),
        ):
            self.scan()

    def test_more_than_400_documents_are_available_in_batches(self):
        for n in range(405):
            put(self.repo / f"docs/{n:04}.md", "text")
        first = self.scan()
        self.assertEqual(first["total"], 405)
        self.assertEqual(len(first["documents"]), 50)
        second = self.scan(offset=50, snapshot=first["snapshot"], batch_size=500)
        self.assertEqual(len(second["documents"]), 355)
        self.assertIsNone(second["next_offset"])
        self.assertFalse(
            {d["path"] for d in first["documents"]} & {d["path"] for d in second["documents"]}
        )

    def test_resume_requires_snapshot_and_rejects_changed_docs(self):
        put(self.repo / "README.md", "original")
        first = self.scan()
        with self.assertRaisesRegex(ValueError, "snapshot"):
            self.scan(offset=1)
        put(self.repo / "README.md", "changed")
        with self.assertRaisesRegex(ValueError, "sources changed"):
            self.scan(snapshot=first["snapshot"])

    def test_existing_items_are_proposed_not_accepted_or_modified(self):
        base = self.init()
        feature = put(
            base / "features/FEAT-001/FEAT-001.story.md",
            frontmatter.render(
                {"id": "FEAT-001", "title": "Refund request", "status": "published"}, "# Refunds\n"
            ),
        )
        put(self.repo / "plans/refund.md", "# Add FEAT-001\n")
        before = feature.read_bytes()
        result = self.scan()
        doc = result["documents"][0]
        self.assertEqual(doc["decision"], "pending")
        self.assertEqual(doc["authority"], "unconfirmed")
        self.assertEqual(doc["proposed_matches"][0]["id"], "FEAT-001")
        self.assertEqual(doc["proposed_matches"][0]["scope"], "REF")
        self.assertEqual(feature.read_bytes(), before)
        self.assertNotIn("# Add", json.dumps(result))
        put(feature, feature.read_text() + "changed\n")
        with self.assertRaisesRegex(ValueError, "sources changed"):
            self.scan(snapshot=result["snapshot"])

    def test_ambiguous_matches_remain_separate_pending_proposals(self):
        base = self.init()
        for ident in ("FEAT-001", "FEAT-002"):
            put(
                base / f"features/{ident}/{ident}.story.md",
                frontmatter.render({"id": ident, "title": "Refund request"}, "x"),
            )
        put(self.repo / "refund.md", "# Refunds")
        doc = self.scan()["documents"][0]
        self.assertEqual(len(doc["proposed_matches"]), 2)
        self.assertEqual(doc["decision"], "pending")

    def test_invalid_batch_and_scope_are_refused(self):
        for kwargs in ({"batch_size": 0}, {"offset": -1}):
            with self.assertRaises(ValueError):
                self.scan(**kwargs)
        self.init()
        with self.assertRaisesRegex(ValueError, "unknown scope"):
            self.scan(scope="OTHER")

    def test_cli_works_before_setup_and_requires_scan_choice(self):
        put(self.repo / "README.md", "# Hello")
        cmd = [sys.executable, str(ANALYZE), "discover", "--cwd", str(self.repo)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "consent_required")
        result = subprocess.run([*cmd, "--confirm-scan"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["total"], 1)

    def test_start_exposes_context_choice_for_fresh_and_existing_workspace(self):
        spec = importlib.util.spec_from_file_location(
            "discovery_start", REPO / "skills/sw-start/scripts/start.py"
        )
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        put(self.repo / "package.json", "{}")
        with patch.object(start.stack, "detect", side_effect=AssertionError("scan before consent")):
            fresh = start.report(self.repo)
        self.assertTrue(fresh["context_intake"]["consent_required"])
        self.assertEqual(fresh["detected_stack"], {})
        self.init()
        self.assertEqual(start.report(self.repo)["context_intake"], discovery.offer())

    def test_analysis_check_never_accepts_high_confidence_evidence(self):
        code = put(self.repo / "test_refund.py", "assert refund(31) is False\n")
        cite = analysis.cite({"repo": self.repo}, "repo/" + code.name, 1)
        text = (
            "---\nkind: analysis\nstatus: draft\n---\n## Criteria\n"
            "| # | Criterion | Intended | Actual | Status | Confidence | Notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            + f"| C-1 | Reject late | owner | {cite} | done | high | |\n"
        )
        target = put(self.repo / "refund.analysis.md", text)
        result = analysis.check(target, {"repo": self.repo})
        self.assertEqual(result["auto_accepted"], [])
        self.assertEqual(result["ask"][0]["row"], "C-1")

    def test_area_and_inventory_include_root_plans_and_nested_text_docs(self):
        spec = importlib.util.spec_from_file_location("discovery_analyze", ANALYZE)
        analyze = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyze)
        base = self.init()
        put(self.repo / "PLAN.md", "# Refund rollout\nRefund limit\n")
        put(self.repo / "plans/refund.rst", "# Refund requirements\n")
        roots = {"repo": self.repo}
        from kitlib import inventory

        docs = inventory.scan_docs(analyze._doc_folders(base, roots))
        self.assertEqual(len(docs), 2)
        self.assertTrue(any(d["at"].startswith("repo/PLAN.md:") for d in docs))
        found = analyze.cmd_area(base, roots, ["refund"], 25)
        self.assertTrue(any(p.startswith("repo/PLAN.md:L") for p in found["docs"]))
        self.assertTrue(any(p.startswith("repo/plans/refund.rst:L") for p in found["docs"]))

    def test_analysis_confirmation_is_bound_to_the_displayed_content(self):
        base = self.init()
        text = (
            "---\nkind: analysis\nstatus: draft\n---\n## Criteria\n"
            "| # | Criterion | Intended | Actual | Status | Confidence | Notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| C-1 | Refund rule | owner | None | missing | low | |\n"
        )
        target = put(base / "01-analysis/as-is/refund.analysis.md", text)
        result = subprocess.run(
            [
                sys.executable,
                str(ANALYZE),
                "confirm",
                "refund",
                "--cwd",
                str(self.repo),
                "--confirmed-by-owner",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        confirmed = analysis.check(target, {})
        self.assertTrue(confirmed["owner_confirmed"])
        self.assertEqual(confirmed["ask"], [])
        target.write_text(target.read_text().replace("Refund rule", "Different rule"))
        self.assertFalse(analysis.check(target, {})["owner_confirmed"])
        self.assertEqual(len(analysis.check(target, {})["ask"]), 1)

    def test_confirm_without_owner_choice_is_refused_without_writes(self):
        self.init()
        result = subprocess.run(
            [sys.executable, str(ANALYZE), "confirm", "refund", "--cwd", str(self.repo)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ask the owner", result.stderr)
        self.assertFalse((self.repo / ".specwright/01-analysis/as-is/refund.analysis.md").exists())
