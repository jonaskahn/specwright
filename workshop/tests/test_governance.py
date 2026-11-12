"""Optional sign-off, plain-words acceptance and the strict mode they sit beside."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from kitlib import (
    frontmatter,
    graph,
    hashing,
    jira_port,
    lifecycle,
    miniyaml,
    publish,
    recordops,
    review,
    schema,
    task_validation,
    workspace,
)
from tests.test_lint_rules import GOOD, doc, lint, update
from tests.test_workflow import FakePort, WorkflowTestCase

ROOT = Path(__file__).resolve().parents[2]
REVIEW_SCRIPT = ROOT / "skills/sw-review/scripts/review.py"
RECORD_SCRIPT = ROOT / "skills/_shared/scripts/record.py"


def load_status():
    spec = importlib.util.spec_from_file_location(
        "governance_status", ROOT / "skills/_shared/scripts/status.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SNAPSHOT = (
    "---\nid: SRC-0001\ntype: snapshot\nstatus: raw\ntitle: Policy\naliases: []\n---\n"
    "Refunds close after 14 days.\n\nPayout needs approval.\n"
)


class SoloTestCase(WorkflowTestCase):
    """A project with no approver at all: the solo developer's workspace."""

    signoff = "optional"
    approvers = ()

    def accept(self):
        updated = review.accept(self.draft, "REF:FEAT-001", self.manifest)
        self.draft.write_text(updated)
        return updated

    def write_plan(self):
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

    def set_mode(self, value):
        workspace.set_governance(self.root, "REF", "signoff", value)


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_a_new_workspace_is_optional_guided_and_markdown(self):
        workspace.init(self.root, "flat", "REF", "Refunds")
        self.assertEqual(
            workspace.governance(self.root, "REF"), {"signoff": "optional", "flow": "guided"}
        )
        self.assertEqual(workspace.output_default(self.root, "REF"), "markdown")
        self.assertEqual(workspace.approver_list(self.root, "REF"), [])

    def test_init_can_start_strict_and_stepwise(self):
        workspace.init(
            self.root, "flat", "REF", "Refunds", governance={"signoff": "required", "flow": "step"}
        )
        self.assertEqual(
            workspace.governance(self.root, "REF"), {"signoff": "required", "flow": "step"}
        )

    def test_jira_setup_is_explicit_and_validated(self):
        workspace.init(self.root, "flat", "REF", "Refunds")
        self.assertEqual(workspace.jira_of(self.root, "REF")["site"], "TBD")
        for site, key in (("", "REF"), ("https://x.atlassian.net", ""), ("TBD", "REF")):
            with self.assertRaises(workspace.WorkspaceError):
                workspace.set_jira(self.root, "REF", site, key, None)
        got = workspace.set_jira(self.root, "REF", "https://x.atlassian.net", "REF", "REF-1")
        want = {"site": "https://x.atlassian.net", "project_key": "REF", "epic": "REF-1"}
        self.assertEqual(got, want)
        self.assertEqual(workspace.jira_of(self.root, "REF"), got)

    def test_set_governance_validates_and_persists(self):
        workspace.init(self.root, "flat", "REF", "Refunds")
        workspace.set_governance(self.root, "REF", "signoff", "required")
        self.assertEqual(workspace.signoff_mode(self.root), "required")
        for key, value in (("signoff", "maybe"), ("flow", "fast"), ("colour", "red")):
            with self.assertRaises(workspace.WorkspaceError):
                workspace.set_governance(self.root, "REF", key, value)

    def test_a_manifest_without_the_block_reads_as_the_defaults(self):
        self.assertEqual(
            workspace.governance_of({"scope": "REF"}), {"signoff": "optional", "flow": "guided"}
        )
        self.assertEqual(
            workspace.governance_of({"governance": {"signoff": "bogus", "flow": "step"}}),
            {"signoff": "optional", "flow": "step"},
        )

    def test_upgrade_keeps_strict_rules_for_a_workspace_with_approvers(self):
        approver = [{"role": "PO", "name": "Lan", "account_id": "1"}]
        workspace.init(self.root, "flat", "REF", "Refunds", approvers=approver)
        path = self.root / "project.yaml"
        data = miniyaml.loads(path.read_text())
        del data["governance"]
        path.write_text(miniyaml.dumps(data))
        workspace.upgrade(self.root, "REF", apply=True)
        self.assertEqual(workspace.signoff_mode(self.root), "required")

    def test_the_cli_reads_and_switches_the_mode(self):
        workspace.init(self.root, "flat", "REF", "Refunds")

        def run(*args):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = workspace.main(["governance", *args, "--cwd", str(self.root)])
            return code, out.getvalue()

        self.assertEqual(json.loads(run("get")[1])["signoff"], "optional")
        self.assertEqual(json.loads(run("set", "signoff", "required")[1])["signoff"], "required")
        self.assertEqual(workspace.signoff_mode(self.root), "required")
        self.assertEqual(run("set", "signoff", "bogus")[0], 2)


class AcceptTests(SoloTestCase):
    def test_accept_needs_no_approver_and_no_url(self):
        updated = self.accept()
        fm, _ = frontmatter.split(updated)
        self.assertEqual(fm["status"], "ready-to-publish")
        digest = hashing.short(hashing.draft_hash(updated))
        self.assertEqual(fm["signoffs"], [f"self | accept | sha256:{digest} | {date.today()}"])
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", updated), "fresh")

    def test_an_accepted_story_can_be_planned(self):
        self.assertTrue(task_validation.planning(self.base, "FEAT-001")["findings"])
        self.accept()
        self.write_plan()
        self.assertTrue(task_validation.planning(self.base, "FEAT-001")["passing"])
        board = lifecycle.feature(self.base, "REF:FEAT-001")
        self.assertEqual((board["station"], board["condition"]), ("plan", "complete"))
        self.assertEqual(board["approval_label"], "accepted")

    def test_an_edit_after_accept_makes_it_stale_and_a_re_accept_fixes_it(self):
        self.accept()
        self.write_plan()
        self.draft.write_text(self.draft.read_text().replace("traceable", "auditable"))
        text = self.draft.read_text()
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", text), "stale")
        self.assertTrue(
            any("stale" in f for f in task_validation.planning(self.base, "FEAT-001")["findings"])
        )
        board = lifecycle.feature(self.base, "REF:FEAT-001")
        self.assertEqual(board["station"], "review")
        self.accept()
        self.assertEqual(
            lifecycle.approval_state(self.base, "FEAT-001", self.draft.read_text()), "fresh"
        )

    def test_a_return_then_a_re_accept_of_the_same_words_is_a_new_line(self):
        self.accept()
        self.set_mode("optional")
        preview = lifecycle.transition(self.base, "REF:FEAT-001", "return-spec")
        lifecycle.transition(self.base, "REF:FEAT-001", "return-spec", confirm=preview["confirm"])
        text = self.draft.read_text()
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", text), "invalidated")
        updated = self.accept()
        fm, _ = frontmatter.split(updated)
        self.assertTrue(fm["signoffs"][-1].endswith("#2"))
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", updated), "fresh")

    def test_required_mode_refuses_a_self_accept(self):
        self.set_mode("required")
        with self.assertRaisesRegex(review.ApprovalError, "required"):
            review.accept(self.draft, "REF:FEAT-001", self.manifest)

    def test_accept_needs_a_passing_lint_gate(self):
        (self.base / "_meta/lint-report.md").write_text("# Lint report\n\n2 blocking error(s).\n")
        with self.assertRaisesRegex(review.ApprovalError, "lint"):
            review.accept(self.draft, "REF:FEAT-001", self.manifest)

    def test_a_published_story_is_not_accepted_again(self):
        self.draft.write_text(frontmatter.update(self.draft.read_text(), {"status": "published"}))
        with self.assertRaisesRegex(review.ApprovalError, "change request"):
            review.accept(self.draft, "REF:FEAT-001", self.manifest)

    def test_the_accept_line_is_not_a_formal_sign_off(self):
        updated = self.accept()
        fm, _ = frontmatter.split(updated)
        self.assertFalse(review.stale(updated, fm["signoffs"], "optional"))
        self.assertTrue(review.stale(updated, fm["signoffs"], "required"))
        forged = ["someone | accept | sha256:" + hashing.short(hashing.draft_hash(updated))]
        self.assertTrue(review.stale(updated, forged, "optional"))

    def test_switching_to_required_reads_the_accept_as_needing_sign_off(self):
        self.accept()
        self.write_plan()
        self.set_mode("required")
        text = self.draft.read_text()
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", text), "stale")
        board = lifecycle.feature(self.base, "REF:FEAT-001")
        self.assertEqual(board["approval_label"], "needs-signoff")
        self.assertEqual(board["station"], "review")
        self.assertFalse(task_validation.planning(self.base, "FEAT-001")["passing"])
        self.set_mode("optional")
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", text), "fresh")

    def test_a_formal_sign_off_still_counts_when_optional(self):
        self.base.joinpath("project.yaml").write_text(
            miniyaml.dumps(
                {
                    **miniyaml.loads(self.manifest.read_text()),
                    "approvers": [{"role": "PO", "name": "Lan", "account_id": "712020:aa11"}],
                }
            )
        )
        evidence = review.Evidence(
            "comment",
            "712020:aa11",
            "https://example.test/c/1",
            review.marker_for(self.draft.read_text(), "REF:FEAT-001"),
        )
        self.draft.write_text(review.promote(self.draft, "REF:FEAT-001", self.manifest, evidence))
        text = self.draft.read_text()
        self.assertEqual(lifecycle.approval_state(self.base, "FEAT-001", text), "fresh")
        self.assertEqual(
            lifecycle.feature(self.base, "REF:FEAT-001")["approval_label"], "signed-off"
        )

    def test_the_script_accepts_and_the_verify_flags_stay_required(self):
        def run(*args):
            return subprocess.run(
                [sys.executable, str(REVIEW_SCRIPT), *args],
                capture_output=True,
                text=True,
                timeout=30,
            )

        common = [
            "--draft",
            str(self.draft),
            "--scope-id",
            "REF:FEAT-001",
            "--manifest",
            str(self.manifest),
        ]
        done = run("accept", *common)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(json.loads(done.stdout)["accepted"])
        self.assertEqual(frontmatter.split(self.draft.read_text())[0]["status"], "ready-to-publish")
        self.assertEqual(run("verify", *common).returncode, 2)


class PublishWithoutPlanTests(SoloTestCase):
    def ctx(self):
        return publish.context(self.root, "FEAT-001", "REF")

    def test_publishing_an_accepted_story_needs_no_tasks(self):
        self.assertTrue(publish.preconditions(self.ctx()))
        self.accept()
        self.assertFalse((self.base / "03-plan/FEAT-001.tasks.md").exists())
        self.assertEqual(publish.preconditions(self.ctx()), [])

    def test_a_stale_accept_blocks_publishing(self):
        self.accept()
        self.draft.write_text(self.draft.read_text().replace("traceable", "auditable"))
        self.assertIn(
            "active approval is absent, stale or invalidated", publish.preconditions(self.ctx())
        )

    def test_request_publish_is_offered_right_after_accept(self):
        self.accept()
        board = lifecycle.feature(self.base, "REF:FEAT-001")
        self.assertIn("request-publish", board["available"])
        preview = lifecycle.transition(self.base, "REF:FEAT-001", "request-publish")
        done = lifecycle.transition(
            self.base, "REF:FEAT-001", "request-publish", confirm=preview["confirm"]
        )
        self.assertTrue(done["applied"])
        self.assertEqual(lifecycle.feature(self.base, "REF:FEAT-001")["station"], "publish")

    def test_the_plan_prints_and_confirm_needs_the_exact_token(self):
        self.accept()
        ctx = self.ctx()
        port = FakePort()
        fields = publish.payload(ctx, {"project": {"key": "PROJ"}})
        plan = jira_port.Plan(publish.operations(ctx, "create", fields, "NEW", ""))
        self.assertTrue(publish.execute(ctx, port, plan, "run1").ok)
        report = {"scope_id": "REF:FEAT-001", "short_hash": "abcd1234"}
        self.assertFalse(publish.confirmed("yes", report))
        self.assertFalse(publish.confirmed("PUBLISH REF:FEAT-001 deadbeef", report))
        self.assertTrue(publish.confirmed("PUBLISH REF:FEAT-001 abcd1234", report))

    def test_required_mode_still_needs_a_formal_sign_off_to_publish(self):
        self.accept()
        self.set_mode("required")
        self.assertTrue(publish.preconditions(self.ctx()))


class RecordTests(SoloTestCase):
    def setUp(self):
        super().setUp()
        (self.base / "00-inbox/SRC-0001.md").write_text(SNAPSHOT)
        self.ctx = recordops.Ctx(self.root, "REF", "sw-shape", today="2026-11-12")

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(RECORD_SCRIPT), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_a_decision_without_a_decider_is_the_owner_in_this_session(self):
        who = recordops.decision_fields(self.ctx, "", "", "", "", "")
        self.assertEqual(who["decided_by"], {"role": "owner", "name": "self", "account_id": ""})
        self.assertEqual((who["evidence_kind"], who["evidence_ref"]), ("session", "2026-11-12"))
        self.assertNotIn("evidence_url", who)

    def test_session_evidence_is_refused_when_sign_off_is_required(self):
        self.set_mode("required")
        with self.assertRaises(recordops.AskError):
            recordops.decision_fields(self.ctx, "", "", "", "", "")
        with self.assertRaisesRegex(recordops.RecordError, "optional"):
            recordops.evidence(self.ctx, "session", "")

    def test_accept_split_runs_without_role_name_or_evidence(self):
        result = self.cli(
            "accept-split", "--item", "Refund request|refund", "--new-epic", "Refunds"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        records = sorted((self.base / "records").glob("DEC-*.md"))
        fm, _ = frontmatter.split(records[-1].read_text())
        self.assertEqual(fm["subtype"], "accepted-split")
        self.assertEqual(fm["decided_by"], {"role": "owner", "name": "self", "account_id": ""})
        self.assertEqual(fm["evidence_kind"], "session")

    def test_accept_split_in_required_mode_still_asks_for_an_approver(self):
        self.set_mode("required")
        result = self.cli("accept-split", "--item", "Refund request", "--new-epic", "Refunds")
        self.assertEqual(result.returncode, 3)

    def test_an_assumed_question_records_its_default_and_does_not_block(self):
        plan = recordops.question_new(
            self.ctx,
            "Which currency?",
            ["FEAT-001"],
            "owner",
            default="VND",
            blocking=False,
            status="assumed",
        )
        recordops.execute(self.ctx, plan, "q-new", "REF:Q-001")
        record = next((self.base / "records").glob("Q-001*.md"))
        fm, body = frontmatter.split(record.read_text())
        self.assertEqual(fm["status"], "assumed")
        self.assertIn("Default applied: VND", body)
        self.assertNotIn("assumed", schema.OPEN_Q)
        from kitlib import blockers

        self.assertEqual(blockers.blocking_questions(self.base, "REF", "FEAT-001"), [])

    def test_an_assumed_question_needs_a_default_and_must_be_non_blocking(self):
        for kwargs in ({"blocking": True, "default": "VND"}, {"blocking": False, "default": ""}):
            with self.assertRaisesRegex(recordops.RecordError, "assumed"):
                recordops.question_new(
                    self.ctx, "Which currency?", ["FEAT-001"], "owner", status="assumed", **kwargs
                )

    def test_an_assumed_question_can_still_be_answered(self):
        plan = recordops.question_new(
            self.ctx,
            "Which currency?",
            ["FEAT-001"],
            "owner",
            default="VND",
            blocking=False,
            status="assumed",
        )
        recordops.execute(self.ctx, plan, "q-new", "REF:Q-001")
        who = recordops.decision_fields(self.ctx, "", "", "", "", "")
        answer = recordops.question_answer(self.ctx, "Q-001", "USD", who)
        self.assertTrue(answer.creates or answer.rewrites)


class LintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def findings(self, document, manifest=None):
        ctx = lint.Context(
            self.base,
            docs=[document],
            gate="publish",
            definitions=lint.definitions_for([document], "REF"),
            manifest=manifest or {},
        )
        return lint.lint_document(document, ctx)

    def decision(self, extra=""):
        head = (
            "---\nid: DEC-001\ntype: dec\nscope: REF\ntitle: Window\naliases: []\n"
            "status: accepted\n"
        )
        return doc(head + extra + "---\n# Decision\n", "records/DEC-001.md")

    def severities(self, document, rule, manifest):
        return {f.sev for f in self.findings(document, manifest) if f.rule == rule}

    def test_l060_and_l061_warn_when_optional_and_block_when_required(self):
        strict = {"governance": {"signoff": "required"}}
        loose = {"governance": {"signoff": "optional"}}
        bare = self.decision()
        self.assertEqual(self.severities(bare, "L-060", loose), {"warn"})
        self.assertEqual(self.severities(bare, "L-060", {}), {"warn"})
        self.assertEqual(self.severities(bare, "L-060", strict), {"error"})
        stranger = self.decision(
            "decided_by:\n  role: PO\n  name: Stranger\nevidence_kind: url\n"
            "evidence_ref: https://e.test/1\n"
        )
        approvers = [{"role": "PO", "name": "Lan", "account_id": "1"}]
        self.assertEqual(
            self.severities(stranger, "L-061", {**loose, "approvers": approvers}), {"warn"}
        )
        self.assertEqual(
            self.severities(stranger, "L-061", {**strict, "approvers": approvers}), {"error"}
        )

    def test_a_session_decision_by_the_owner_is_clean_when_optional(self):
        owner = self.decision(
            "decided_by:\n  role: owner\n  name: self\nevidence_kind: session\n"
            "evidence_ref: 2026-11-12\n"
        )
        self.assertEqual(self.findings(owner, {"governance": {"signoff": "optional"}}), [])
        approvers = [{"role": "PO", "name": "Lan", "account_id": "1"}]
        named = {"governance": {"signoff": "optional"}, "approvers": approvers}
        self.assertEqual(self.findings(owner, named), [])
        strict = {"governance": {"signoff": "required"}, "approvers": approvers}
        self.assertIn("L-061", {f.rule for f in self.findings(owner, strict)})
        flagged = {f.rule for f in self.findings(owner, {"governance": {"signoff": "required"}})}
        self.assertIn("L-060", flagged)

    def test_l045_is_met_by_a_fresh_accept_only_when_optional(self):
        base = update(GOOD, status="ready-to-publish")
        digest = hashing.short(hashing.draft_hash(base))
        accepted = doc(update(base, signoffs=[f"self | accept | sha256:{digest} | 2026-11-12"]))
        manifest = {"governance": {"signoff": "optional"}}
        self.assertNotIn("L-045", {f.rule for f in self.findings(accepted, manifest)})
        strict = {"governance": {"signoff": "required"}}
        self.assertIn("L-045", {f.rule for f in self.findings(accepted, strict)})
        stale = doc(update(base, signoffs=["self | accept | sha256:000000000000 | 2026-11-12"]))
        self.assertIn("L-045", {f.rule for f in self.findings(stale, manifest)})


class StatusTests(SoloTestCase):
    status = load_status()

    def test_the_status_report_names_the_accept_and_the_label(self):
        self.accept()
        graph.build(self.root, "REF")
        feature = self.status.build_report(self.root)["features"][0]
        self.assertEqual(feature["signoff"], "accepted")
        self.assertEqual(feature["state_label"], "accepted")
        self.assertEqual(feature["next"], "sw-plan")
        self.set_mode("required")
        graph.build(self.root, "REF")
        feature = self.status.build_report(self.root)["features"][0]
        self.assertEqual(feature["signoff"], "needs-signoff")
        self.assertEqual(feature["next"], "sw-review")


if __name__ == "__main__":
    unittest.main()
