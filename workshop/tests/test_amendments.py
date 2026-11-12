"""An answer that changes saved wording becomes a tracked amendment until it is applied."""

from kitlib import frontmatter, graph, graph_query, hashing, recordops, rtm, schema
from tests.test_workflow import WorkflowTestCase

OLD = "days 8-14 yield 50%"
NEW = "days 8-14 yield 25%"


class AmendmentTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.ctx = recordops.Ctx(self.root, "REF", "sw-shape", today="2026-11-12")

    def run_plan(self, plan, action="x"):
        return recordops.execute(self.ctx, plan, action, "REF")

    def amend(self, **kwargs):
        values = {"feat": "FEAT-001", "quote": OLD, "proposed": NEW, "decision": "DEC-001"}
        values.update(kwargs)
        plan, identity = recordops.amendment_new(self.ctx, **values)
        self.run_plan(plan, "amend-new")
        return identity

    def record(self, ident):
        path = next((self.base / "records").glob(f"{ident}--*.md"))
        return frontmatter.split(path.read_text())

    def test_a_new_amendment_names_the_feature_and_both_wordings(self):
        ident = self.amend()
        fm, body = self.record(ident)
        self.assertEqual(
            (ident, fm["status"], fm["affects"]), ("AMD-001", "proposed", ["FEAT-001"])
        )
        self.assertFalse(fm["requires_cr"])
        self.assertIn(f"> {OLD}", body)
        self.assertIn(f"> {NEW}", body)

    def test_context_lists_the_amendment_for_the_feature(self):
        self.amend()
        graph.build(self.root, "REF")
        lines = graph_query.context(
            graph_query.Store(self.root, "REF"), "REF:FEAT-001", False, 4000
        )
        self.assertTrue(any(line.startswith("amendment: REF:AMD-001") for line in lines), lines)

    def test_wording_not_in_the_story_or_unchanged_is_refused(self):
        with self.assertRaisesRegex(recordops.RecordError, "not in the saved story"):
            recordops.amendment_new(self.ctx, "FEAT-001", "no such text", NEW)
        with self.assertRaisesRegex(recordops.RecordError, "equals the current"):
            recordops.amendment_new(self.ctx, "FEAT-001", OLD, OLD)
        with self.assertRaisesRegex(recordops.RecordError, "no saved story"):
            recordops.amendment_new(self.ctx, "FEAT-009", OLD, NEW)

    def test_an_answer_can_carry_its_amendments(self):
        (self.base / "records").mkdir(exist_ok=True)
        plan = recordops.question_new(self.ctx, "Which tier?", ["FEAT-001"], "PO", status="open")
        self.run_plan(plan, "q-new")
        who = recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/1")
        answer = recordops.question_answer(
            self.ctx, "Q-001", "Use 25%.", who, [f"FEAT-001||{OLD}||{NEW}"]
        )
        self.run_plan(answer, "q-answer")
        self.assertEqual(answer.made, ["DEC-001", "AMD-001"])
        self.assertEqual(self.record("AMD-001")[0]["decision"], "DEC-001")

    def test_applying_needs_the_draft_to_carry_the_new_wording(self):
        ident = self.amend()
        with self.assertRaisesRegex(recordops.RecordError, "still carries the current wording"):
            recordops.amendment_close(self.ctx, ident, "applied")
        text = self.draft.read_text()
        self.draft.write_text(text.replace(OLD, NEW))
        self.run_plan(recordops.amendment_close(self.ctx, ident, "applied"), "amend-apply")
        fm, body = self.record(ident)
        self.assertEqual(fm["status"], "applied")
        self.assertEqual(fm["applied_hash"], hashing.draft_hash(self.draft.read_text()))
        self.assertIn("fresh approval", body)
        with self.assertRaises(recordops.RecordError):
            recordops.amendment_close(self.ctx, ident, "rejected", "late")

    def test_a_draft_that_lost_both_wordings_cannot_be_applied(self):
        ident = self.amend()
        self.draft.write_text(self.draft.read_text().replace(OLD, "something else entirely"))
        with self.assertRaisesRegex(recordops.RecordError, "does not carry the proposed"):
            recordops.amendment_close(self.ctx, ident, "applied")

    def test_rejecting_needs_a_reason_and_keeps_the_record(self):
        ident = self.amend()
        with self.assertRaises(recordops.RecordError):
            recordops.amendment_close(self.ctx, ident, "rejected", " ")
        self.run_plan(recordops.amendment_close(self.ctx, ident, "rejected", "PO declined"))
        self.assertEqual(self.record(ident)[0]["status"], "rejected")

    def test_a_published_feature_needs_a_change_request(self):
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md",
            "REF:FEAT-001",
            {"State": "published", "Jira key": "PROJ-14"},
            "sw-publish",
        )
        fm, body = self.record(self.amend())
        self.assertTrue(fm["requires_cr"])
        self.assertIn("raise a change request", body)
        self.assertIn("amendment", schema.STATUSES)
