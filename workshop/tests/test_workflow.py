"""Offline checks for approval, publish safety and snapshot drift."""

import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, hashing, jira_port, publish, review, tables, workspace

ROOT = Path(__file__).resolve().parents[2]

DRAFT = """---
id: FEAT-001
type: feature
scope: REF
status: in-review
jira_summary: Request a refund for a delivered order
jira_labels: [specwright, feat:FEAT-001, proj:REF]
bo: [BO-001]
---
## Goal
As a customer, I want a refund so that repayment is traceable. BO-001.

## Acceptance criteria
### AC-001-1 — Eligible request
Given order "ORD-1001" for 1,200,000 VND was delivered 5 days ago
When the customer submits a refund request
Then a request for 1,200,000 VND is stored with status "Pending approval"

### AC-001-2 — Expired request
Given order "ORD-1002" was delivered 15 days ago
When the customer submits a refund request
Then the message "The 14-day refund window for this order has ended." is shown

## Business rules
- BR-001: days 0-7 yield 100%; days 8-14 yield 50%; later days yield none.
  Example: 1,200,000 VND at day 9 yields 600,000 VND.

## Edge cases and error behavior
- IF the order is 15 days old THEN no request is stored.

## Non-functional
- NFR-REF-001: p95 response time is below 2 seconds at 200 concurrent users for 15 minutes.

## UI/UX
- States: default, empty, loading, error.

## Out of scope
- Partial-item refunds — separate allocation rules.

## Dependencies and relations
- None

## Open questions
None

## DoR checklist
- [x] Goal links BO-001
- [x] Concrete acceptance criteria

## Identity
Draft hash: placeholder
Dev consumer check: yes
QA consumer check: yes
"""


class WorkflowTestCase(unittest.TestCase):
    """A project with one approver. Strict by default so these tests keep proving governed mode."""

    signoff = "required"
    approvers = ({"role": "PO", "name": "Lan", "account_id": "712020:aa11"},)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        workspace.init(
            self.root,
            "flat",
            "REF",
            "Refunds",
            project_key="PROJ",
            approvers=[dict(a) for a in self.approvers],
            governance={"signoff": self.signoff},
        )
        self.base = self.root
        self.draft = self.root / "02-drafts" / "FEAT-001.story.md"
        self.draft.write_text(DRAFT)
        card = (
            "---\nid: FEAT-001\ntype: feature\nscope: REF\nstatus: in-review\ncard: true\n"
            "home: repo\nlinks: [https://example.test/card]\n---\n## Summary\nRefund request.\n"
        )
        (self.root / "02-drafts" / "FEAT-001.card.md").write_text(card)
        (self.root / "_meta" / "lint-report.md").write_text(
            "# Lint report\n\nScope: REF · Gate: publish\n\n0 blocking error(s).\n"
        )
        self.manifest = self.root / "project.yaml"


class ReviewTests(WorkflowTestCase):
    def evidence(self, **kwargs):
        values = {
            "kind": "comment",
            "author": "712020:aa11",
            "url": "https://example.atlassian.net/browse/PROJ-14?focusedCommentId=1",
            "body": review.marker_for(DRAFT, "REF:FEAT-001"),
        }
        values.update(kwargs)
        return review.Evidence(**values)

    def test_valid_marker_binds_to_the_current_draft(self):
        result = review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, self.evidence())
        self.assertEqual(result["status"], "ready-to-publish")
        self.assertIn("712020:aa11", result["signoff"])

    def test_wrong_hash_or_author_is_rejected(self):
        with self.assertRaises(review.ApprovalError):
            review.verify_evidence(
                DRAFT,
                "REF:FEAT-001",
                self.manifest,
                self.evidence(body="[sw:approve REF:FEAT-001 sha256:000000000000]"),
            )
        with self.assertRaises(review.ApprovalError):
            review.verify_evidence(
                DRAFT, "REF:FEAT-001", self.manifest, self.evidence(author="someone-else")
            )
        with self.assertRaises(review.ApprovalError):
            review.verify_evidence(
                DRAFT, "REF:FEAT-001", self.manifest, self.evidence(url="http://example.test")
            )

    def test_role_and_name_must_match_the_configured_approver(self):
        ok = self.evidence(role="po", name="LAN")
        self.assertEqual(
            review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, ok)["status"],
            "ready-to-publish",
        )
        for wrong in ({"role": "Dev"}, {"name": "Someone Else"}):
            with self.assertRaisesRegex(review.ApprovalError, "does not match"):
                review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, self.evidence(**wrong))

    def allow(self, kind):
        from kitlib import miniyaml

        data = miniyaml.loads(self.manifest.read_text())
        data["evidence"]["allowed_kinds"].append(kind)
        self.manifest.write_text(miniyaml.dumps(data))

    def test_chat_needs_opt_in_and_meeting_needs_a_session_reference(self):
        chat = self.evidence(kind="chat", session_ref="thread-9")
        with self.assertRaisesRegex(review.ApprovalError, "does not accept"):
            review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, chat)
        self.allow("chat")
        for kind in ("chat", "meeting"):  # a meeting is allowed by default
            with self.assertRaisesRegex(review.ApprovalError, "session reference"):
                review.verify_evidence(
                    DRAFT, "REF:FEAT-001", self.manifest, self.evidence(kind=kind)
                )
            evidence = self.evidence(kind=kind, session_ref="ref-9")
            result = review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, evidence)
            self.assertTrue(result["signoff"].endswith("| session:ref-9"), kind)
            self.assertFalse(review.stale(DRAFT, [result["signoff"]]))

    def test_chat_evidence_still_needs_the_marker_and_an_https_permalink(self):
        self.allow("chat")
        for bad in (
            self.evidence(kind="chat", session_ref="t", body="approved!"),
            self.evidence(kind="chat", session_ref="t", url="http://chat.test/1"),
        ):
            with self.assertRaises(review.ApprovalError):
                review.verify_evidence(DRAFT, "REF:FEAT-001", self.manifest, bad)

    def test_the_script_requires_the_approver_role_and_name(self):
        import subprocess
        import sys

        script = ROOT / "skills/sw-review/scripts/review.py"
        base = [
            sys.executable,
            str(script),
            "verify",
            "--draft",
            str(self.draft),
            "--scope-id",
            "REF:FEAT-001",
            "--manifest",
            str(self.manifest),
            "--author",
            "712020:aa11",
            "--url",
            "https://example.test/c/1",
            "--kind",
            "comment",
            "--body",
            review.marker_for(self.draft.read_text(), "REF:FEAT-001"),
        ]
        missing = subprocess.run(base, capture_output=True, text=True, timeout=30)
        self.assertEqual(missing.returncode, 2)
        full = subprocess.run(
            [*base, "--role", "PO", "--name", "Lan"], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(full.returncode, 0, full.stderr)
        wrong = subprocess.run(
            [*base, "--role", "PO", "--name", "Mallory"], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(wrong.returncode, 2)

    def test_promotion_keeps_the_body_hash_stable(self):
        before = hashing.draft_hash(DRAFT)
        updated = review.promote(self.draft, "REF:FEAT-001", self.manifest, self.evidence())
        fm, _ = frontmatter.split(updated)
        self.assertEqual(fm["status"], "ready-to-publish")
        self.assertEqual(hashing.draft_hash(updated), before)
        self.assertFalse(review.stale(updated, fm["signoffs"]))

    def test_changed_draft_makes_a_saved_signoff_stale(self):
        updated = review.promote(self.draft, "REF:FEAT-001", self.manifest, self.evidence())
        fm, _ = frontmatter.split(updated)
        self.assertTrue(review.stale(updated.replace("BO-001", "BO-002"), fm["signoffs"]))


class FakePort(jira_port.Port):
    def __init__(self):
        self.keys = []
        self.calls = []
        self.updated = "t1"

    def get_issue(self, key):
        return {"key": key, "fields": {"updated": self.updated}}

    def search_by_label(self, project, label):
        self.calls.append(("search", project, label))
        return [{"key": key} for key in self.keys]

    def list_changelog(self, key):
        return []

    def list_comments(self, key):
        return []

    def create_issue(self, fields):
        self.calls.append(("create", fields))
        return {"key": "PROJ-14"}

    def edit_issue(self, key, fields):
        self.calls.append(("edit", key, fields))
        return {"key": key}

    def add_link(self, payload):
        return payload

    def attach_file(self, key, path):
        return {"key": key}

    def set_property(self, key, property_key, value):
        self.calls.append(("property", key, property_key, value))
        return {}

    def get_property(self, key, property_key):
        return {"id": "REF:FEAT-001"}


class PublishTests(WorkflowTestCase):
    def ctx(self):
        return publish.context(self.root, "FEAT-001", "REF")

    def test_preconditions_reject_unpromoted_drafts(self):
        self.assertTrue(publish.preconditions(self.ctx()))

    def promote(self):
        text = review.promote(
            self.draft,
            "REF:FEAT-001",
            self.manifest,
            review.Evidence(
                "comment",
                "712020:aa11",
                "https://example.atlassian.net/c/1",
                review.marker_for(DRAFT, "REF:FEAT-001"),
            ),
        )
        self.draft.write_text(text)
        (self.root / "03-plan/FEAT-001.plan.md").write_text(
            "# Implementation plan\n\nImplement both acceptance criteria.\n"
        )
        (self.root / "03-plan/FEAT-001.tasks.md").write_text(
            frontmatter.render(
                {"feat": "FEAT-001", "status": "ready", "spec_hash": hashing.draft_hash(text)},
                "\n".join(
                    f"### TASK-001-{n} — Implement criterion\nTraces to: AC-001-{n}\n"
                    "Done when: criterion is verified\n"
                    for n in (1, 2)
                ),
            )
        )

    def test_identity_checks_registry_then_label_then_property(self):
        ctx = self.ctx()
        port = FakePort()
        self.assertEqual(publish.identity(ctx, port, "PROJ", "FEAT-001"), "NEW")
        port.keys = ["PROJ-14"]
        self.assertEqual(publish.identity(ctx, port, "PROJ", "FEAT-001"), "PROJ-14")
        port.keys = ["PROJ-14", "PROJ-15"]
        with self.assertRaises(publish.PublishError):
            publish.identity(ctx, port, "PROJ", "FEAT-001")
        registry = tables.parse(ctx.registry.read_text()).table
        registry.upsert("REF:FEAT-001", {"Jira key": "PROJ-99"})
        ctx.registry.write_text(tables.Document("", registry, "").render())
        self.assertEqual(publish.identity(ctx, port, "PROJ", "FEAT-001"), "PROJ-99")

    def test_confirmation_must_match_scope_and_report_hash(self):
        report = {"scope_id": "REF:FEAT-001", "short_hash": "abcd1234"}
        self.assertTrue(publish.confirmed("PUBLISH REF:FEAT-001 abcd1234", report))
        self.assertFalse(publish.confirmed("PUBLISH REF:FEAT-001 deadbeef", report))
        self.assertFalse(publish.confirmed("yes", report))

    def test_create_plan_executes_only_hash_bound_dependent_writes(self):
        self.promote()
        ctx = self.ctx()
        self.assertEqual(publish.preconditions(ctx), [])
        port = FakePort()
        fields = publish.payload(ctx, {"project": {"key": "PROJ"}})
        ops = publish.operations(ctx, "create", fields, "NEW", "")
        plan = jira_port.Plan(ops)
        self.assertEqual([op.kind for op in ops], ["create", "set_property"])
        outcome = publish.execute(ctx, port, plan, "run1")
        self.assertTrue(outcome.ok)
        self.assertEqual([call[0] for call in port.calls], ["create", "property"])
        self.assertEqual(port.calls[1][1], "PROJ-14")
        self.assertEqual(len(jira_port.Plan(ops).plan_hash), 64)
        self.assertIn("INTENT", ctx.log.read_text())
        self.assertIn("RESULT", ctx.log.read_text())

    def test_registry_is_not_updated_while_preconditions_fail(self):
        before = self.ctx().registry.read_bytes()
        self.assertTrue(publish.preconditions(self.ctx()))
        self.assertEqual(self.ctx().registry.read_bytes(), before)

    def test_record_writes_local_indexes_after_success(self):
        ctx = self.ctx()
        publish.record(ctx, "PROJ-14", DRAFT)
        registry = tables.parse(ctx.registry.read_text()).table
        self.assertEqual(registry.get("REF:FEAT-001", "Jira key"), "PROJ-14")
        matrix = tables.parse(ctx.rtm.read_text()).table
        self.assertEqual(matrix.get("REF:FEAT-001", "Jira [sw-publish]"), "PROJ-14")
        card, _ = frontmatter.split(ctx.card.read_text())
        self.assertEqual(card["status"], "published")
