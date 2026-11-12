"""Local lifecycle decisions must survive cache rebuilds without remote calls."""

import importlib.util
import json
import subprocess
from unittest.mock import patch

from kitlib import (
    frontmatter,
    graph,
    graph_query,
    hashing,
    lifecycle,
    publish,
    review,
    task_validation,
    workspace,
)
from tests.test_workflow import DRAFT, WorkflowTestCase


class LifecycleTests(WorkflowTestCase):
    def apply(self, action):
        preview = lifecycle.transition(self.base, "REF:FEAT-001", action)
        return lifecycle.transition(self.base, "REF:FEAT-001", action, confirm=preview["confirm"])

    def approve(self, url="https://example.test/approval/1"):
        text = self.draft.read_text()
        evidence = review.Evidence(
            "comment", "712020:aa11", url, review.marker_for(text, "REF:FEAT-001")
        )
        self.draft.write_text(review.promote(self.draft, "REF:FEAT-001", self.manifest, evidence))

    def plan(self):
        text = self.draft.read_text()
        (self.base / "03-plan/FEAT-001.plan.md").write_text("# Plan\nImplement criteria.\n")
        tasks = "\n".join(
            f"### TASK-001-{n} — Criterion\nTraces to: AC-001-{n}\n"
            "Done when: observable criterion verified\n"
            for n in (1, 2)
        )
        (self.base / "03-plan/FEAT-001.tasks.md").write_text(
            frontmatter.render(
                {"feat": "FEAT-001", "status": "ready", "spec_hash": hashing.draft_hash(text)},
                tasks,
            )
        )

    def test_deferral_survives_restart_and_rebuild(self):
        self.approve()
        self.plan()
        self.assertTrue(task_validation.planning(self.base, "FEAT-001")["passing"])
        self.apply("request-publish")
        self.assertEqual(lifecycle.feature(self.base, "REF:FEAT-001")["station"], "publish")
        self.apply("defer-publish")
        graph.build(self.root, "REF")
        row = graph_query.board(graph_query.Store(self.root, "REF"))[0]
        self.assertEqual((row["station"], row["condition"]), ("plan", "complete"))
        self.assertEqual(len(lifecycle.decisions(self.base, "REF:FEAT-001")), 2)

    def test_rollback_invalidates_approval_without_faking_stale_hash(self):
        self.approve()
        self.plan()
        digest = hashing.draft_hash(self.draft.read_text())
        tasks = (self.base / "03-plan/FEAT-001.tasks.md").read_bytes()
        self.apply("return-spec")
        self.assertEqual(hashing.draft_hash(self.draft.read_text()), digest)
        self.assertEqual((self.base / "03-plan/FEAT-001.tasks.md").read_bytes(), tasks)
        self.assertEqual(
            lifecycle.approval_state(self.base, "FEAT-001", self.draft.read_text()), "invalidated"
        )
        with self.assertRaises(review.ApprovalError):
            self.approve()
        self.approve("https://example.test/approval/2")
        self.assertEqual(
            lifecycle.approval_state(self.base, "FEAT-001", self.draft.read_text()), "fresh"
        )

    def test_confirmation_is_bound_to_current_inputs(self):
        preview = lifecycle.transition(self.base, "REF:FEAT-001", "return-spec")
        self.draft.write_text(self.draft.read_text().replace("traceable", "auditable"))
        with self.assertRaisesRegex(ValueError, "confirmation"):
            lifecycle.transition(
                self.base, "REF:FEAT-001", "return-spec", confirm=preview["confirm"]
            )
        self.assertEqual(lifecycle.decisions(self.base, "REF:FEAT-001"), [])

    def test_shape_reopen_and_accept_survive_rebuild(self):
        self.draft.write_text(frontmatter.update(DRAFT, {"status": "draft"}))
        self.apply("reopen-shape")
        graph.build(self.root, "REF")
        self.assertEqual(
            graph_query.board(graph_query.Store(self.root, "REF"))[0]["station"], "shape"
        )
        self.apply("accept-slice")
        self.assertEqual(lifecycle.feature(self.base, "REF:FEAT-001")["station"], "spec")

    def test_published_story_rewind_is_refused(self):
        publish.record(publish.context(self.root, "FEAT-001", "REF"), "PROJ-14", DRAFT)
        with self.assertRaisesRegex(ValueError, "amendment"):
            lifecycle.transition(self.base, "REF:FEAT-001", "return-spec")

    def test_pending_transaction_blocks_board(self):
        (self.base / "_meta/lifecycle-pending.json").write_text("{}")
        self.assertEqual(lifecycle.feature(self.base, "REF:FEAT-001")["condition"], "unknown")

    def test_forked_records_are_not_ordered_by_filename(self):
        self.apply("return-spec")
        path = next((self.base / "records").glob("DEC-001*.md"))
        fm, body = frontmatter.split(path.read_text())
        fm["id"] = "DEC-002"
        (path.parent / "DEC-002.md").write_text(frontmatter.render(fm, body))
        self.assertEqual(lifecycle.feature(self.base, "REF:FEAT-001")["condition"], "unknown")

    def test_same_length_edits_invalidate_graph(self):
        graph.build(self.root, "REF")
        store = graph_query.Store(self.root, "REF")
        self.assertEqual(store.freshness(), "fresh")
        self.draft.write_text(self.draft.read_text().replace("traceable", "auditable"))
        self.assertEqual(store.freshness(), "stale")
        with self.assertRaises(graph_query.QueryError):
            graph_query.board(store)

    def test_reserved_registry_feature_is_visible(self):
        from kitlib import rtm

        rtm.registry_upsert(
            self.base / "_meta/id-registry.md", "REF:FEAT-002", {"Kind": "story"}, "sw-spec"
        )
        graph.build(self.root, "REF")
        rows = graph_query.board(graph_query.Store(self.root, "REF"))
        reserved = next(r for r in rows if r["id"] == "REF:FEAT-002")
        self.assertEqual((reserved["station"], reserved["condition"]), ("spec", "not-started"))

    def test_publication_cannot_skip_plan(self):
        self.approve()
        ctx = publish.context(self.root, "FEAT-001", "REF")
        self.assertTrue(publish.preconditions(ctx))
        with self.assertRaises(ValueError):
            lifecycle.transition(self.base, "REF:FEAT-001", "request-publish")

    def test_graph_schema_mismatch_blocks_resume(self):
        graph.build(self.root, "REF")
        path = self.base / "_meta/graph/manifest.json"
        data = json.loads(path.read_text())
        data["schema_version"] = 0
        path.write_text(json.dumps(data))
        self.assertEqual(graph_query.Store(self.root, "REF").freshness(), "incompatible")

    def test_git_reuses_parent_and_requires_repo_for_embedded(self):
        child = self.root / "docs"
        workspace.init(child, "flat", "DOC", "Docs")
        self.assertFalse((child / ".git").exists())
        result = subprocess.run(
            ["git", "-C", str(child), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), str(self.root))
        with (
            patch("kitlib.workspace.shutil.which", return_value=None),
            self.assertRaises(workspace.WorkspaceError),
        ):
            workspace.init(self.root / "missing", "flat", "NEW", "Missing")
        self.assertFalse((self.root / "missing/project.yaml").exists())

    def test_mixed_stations_and_explicit_resume_do_not_move_siblings(self):
        from pathlib import Path

        other = self.base / "02-drafts/FEAT-002.story.md"
        other.write_text(frontmatter.update(DRAFT, {"id": "FEAT-002", "status": "draft"}))
        self.approve()
        self.plan()
        graph.build(self.root, "REF")
        script = Path(__file__).resolve().parents[1] / "skills/sw-start/scripts/start.py"
        spec = importlib.util.spec_from_file_location("board_start", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.report(self.root)
        self.assertEqual(report["scopes_state"][0]["next"][0], "choose item")
        before = other.read_bytes()
        report = module.report(self.root, "REF:FEAT-001")
        self.assertEqual(report["scopes_state"][0]["next"][0], "sw-plan")
        self.assertEqual(other.read_bytes(), before)
        self.assertEqual(
            module.report(self.root, "FEAT-002")["scopes_state"][0]["next"][0], "sw-spec"
        )

    def test_accepted_split_keeps_reserved_membership_visible(self):
        from kitlib import rtm

        epic = self.base / "01-analysis/epics/EPIC-001.md"
        epic.write_text(
            frontmatter.render(
                {"id": "EPIC-001", "type": "epic", "scope": "REF", "status": "approved"},
                "# Refunds\n",
            )
        )
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md", "REF:FEAT-002", {"Kind": "story"}, "sw-spec"
        )
        (self.base / "records/DEC-001.md").write_text(
            frontmatter.render(
                {
                    "id": "DEC-001",
                    "type": "dec",
                    "status": "accepted",
                    "subtype": "accepted-split",
                    "scope": "REF",
                    "epic": "REF:EPIC-001",
                    "features": ["REF:FEAT-002"],
                    "evidence_url": "https://example.test/split/1",
                },
                "# Accepted split\n",
            )
        )
        graph.build(self.root, "REF")
        rows = graph_query.board(graph_query.Store(self.root, "REF"), "REF:EPIC-001")
        self.assertEqual({r["id"] for r in rows}, {"REF:EPIC-001", "REF:FEAT-002"})

    def test_remote_uncertainty_refuses_local_rollback(self):
        from kitlib import writelog

        writelog.intent(
            self.base / "_meta/write-log.md", "abcd", 1, "sw-publish", "create", "REF:FEAT-001"
        )
        with self.assertRaisesRegex(ValueError, "recovery"):
            lifecycle.transition(self.base, "REF:FEAT-001", "return-spec")

    def test_worktree_git_file_is_reused(self):
        worktree = self.root.parent / (self.root.name + "-worktree")
        subprocess.run(
            [
                "git",
                "-C",
                str(self.root),
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.test",
                "commit",
                "--allow-empty",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "worktree", "add", "--detach", str(worktree)],
            check=True,
            capture_output=True,
        )
        try:
            self.assertTrue((worktree / ".git").is_file())
            workspace.init(worktree, "flat", "WT", "Worktree", layout="embedded")
            self.assertFalse((worktree / ".specwright/.git").exists())
        finally:
            subprocess.run(
                ["git", "-C", str(self.root), "worktree", "remove", "--force", str(worktree)],
                check=True,
                capture_output=True,
            )

    def test_draft_questions_recommend_spec(self):
        script = (
            __import__("pathlib").Path(__file__).resolve().parents[1]
            / "skills/_shared/scripts/status.py"
        )
        spec = importlib.util.spec_from_file_location("board_status", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(
            module.recommend("draft", "pass", "clean", "unknown", ["Q-001"], [])[0], "sw-spec"
        )
