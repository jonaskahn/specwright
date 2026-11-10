import json
import tempfile
import unittest
from pathlib import Path

from kitlib import adf, jira_diff, jira_port, writelog

STORY = """# Title

## Goal
As a customer, I want a refund.

## Acceptance criteria
### AC-001-1 — Timely refund
Given order "ORD-1001" of 1,200,000 VND
When the customer submits a refund
Then the amount is 1,200,000 VND

## Business rules
- BR-001 applies with \`code\` and **bold** text.

## DoR checklist
- [ ] Goals link a BO
"""


class AdfTests(unittest.TestCase):
    def test_story_subset_round_trips(self):
        doc = adf.md_to_adf(STORY)
        adf.validate_adf(doc)
        restored, found = adf.adf_to_md(doc)
        self.assertEqual(found, [])
        self.assertEqual(restored, adf.adf_to_md(adf.md_to_adf(restored))[0])
        self.assertIn("AC-001-1 — Timely refund", restored)
        self.assertIn("[ ] Goals link a BO", restored)
        self.assertIn("BR-001", restored)

    def test_unsupported_nodes_are_visible_and_warned(self):
        doc = {
            "version": 1,
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Keep me"}]},
                {
                    "type": "panel",
                    "content": [
                        {"type": "paragraph", "content": [{"type": "text", "text": "Inside"}]}
                    ],
                },
            ],
        }
        text, warnings = adf.adf_to_md(doc)
        self.assertIn("Keep me", text)
        self.assertIn("Inside", text)
        self.assertIn("<!-- adf:panel -->", text)
        self.assertIn("unsupported-node:panel", warnings)

    def test_invalid_documents_are_rejected(self):
        with self.assertRaises(ValueError):
            adf.validate_adf({"version": 2, "type": "doc", "content": []})
        with self.assertRaises(ValueError):
            adf.validate_adf({"version": 1, "type": "doc", "content": [{"type": "unknown"}]})


class DiffTests(unittest.TestCase):
    def test_all_four_section_actions_and_exit_codes(self):
        self.assertEqual(jira_diff.action("a", "a", "a"), "no-op")
        self.assertEqual(jira_diff.action("a", "a", "b"), "apply")
        self.assertEqual(jira_diff.action("a", "b", "a"), "keep-theirs")
        self.assertEqual(jira_diff.action("a", "b", "c"), "CONFLICT")
        base = "## Goal\nold\n"
        result = jira_diff.plan(base, base, "## Goal\nours\n", scope_id="REF:FEAT-001")
        self.assertEqual(jira_diff.exit_code(result), 1)
        self.assertIn("PUBLISH REF:FEAT-001 " + result["short_hash"], jira_diff.render_plan(result))
        conflicted = jira_diff.plan("## Goal\nold\n", "## Goal\ntheirs\n", "## Goal\nours\n")
        self.assertEqual(jira_diff.exit_code(conflicted), 4)
        remote = jira_diff.plan("## Goal\nold\n", "## Goal\ntheirs\n", "## Goal\nold\n")
        self.assertEqual(jira_diff.exit_code(remote), 3)

    def test_plan_hash_is_stable_and_content_sensitive(self):
        first = jira_diff.plan("", "", "## Goal\nours\n", scope_id="REF:FEAT-001")
        second = jira_diff.plan("", "", "## Goal\nours\n", scope_id="REF:FEAT-001")
        changed = jira_diff.plan("", "", "## Goal\nother\n", scope_id="REF:FEAT-001")
        self.assertEqual(first["plan_hash"], second["plan_hash"])
        self.assertNotEqual(first["plan_hash"], changed["plan_hash"])
        self.assertEqual(len(first["short_hash"]), 8)

    def test_classify_returns_stable_drift_classes(self):
        base = {
            "key": "PROJ-14",
            "fields": {"description": "old", "status": {"name": "To Do"}},
            "comments": [{"id": "1"}],
        }
        current = {
            "key": "PROJ-14",
            "fields": {"description": "new", "status": {"name": "In Progress"}},
            "comments": [{"id": "1"}, {"id": "2"}],
            "identity": "changed",
        }
        classes = jira_diff.classify(base, current)
        self.assertEqual(
            classes,
            ["content-edited", "status-changed", "comments-new", "identity"],
        )


class FakePort(jira_port.Port):
    def __init__(self):
        self.calls = []
        self.found = []

    def get_issue(self, key):
        self.calls.append(("get_issue", key))
        return {"fields": {"updated": "t1"}}

    def search_by_label(self, project, label):
        self.calls.append(("search_by_label", project, label))
        return self.found

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
        return {"key": key, "path": path}

    def set_property(self, key, property_key, value):
        return {"key": key}

    def get_property(self, key, property_key):
        return {}


class PlanExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.log = Path(self.tmp.name) / "write-log.md"

    def test_plan_hash_covers_order_and_contents(self):
        first = jira_port.Plan([jira_port.Operation("edit", {"key": "A", "fields": {}}, "t1")])
        second = jira_port.Plan([jira_port.Operation("edit", {"key": "A", "fields": {}}, "t1")])
        self.assertEqual(first.plan_hash, second.plan_hash)
        with self.assertRaises(ValueError):
            jira_port.Plan(first.operations, "wrong")

    def test_edit_checks_updated_and_logs_intent_before_result(self):
        port = FakePort()
        plan = jira_port.Plan([jira_port.Operation("edit", {"key": "A", "fields": {}}, "t1")])
        outcome = jira_port.apply_plan(port, plan, self.log, "run1", "REF:FEAT-001")
        self.assertTrue(outcome.ok)
        self.assertEqual(port.calls[0], ("get_issue", "A"))
        entries = writelog.read(self.log)
        self.assertEqual([e.kind for e in entries], ["INTENT", "RESULT"])
        self.assertEqual(writelog.unfinished(self.log), [])

    def test_changed_updated_stops_before_a_write(self):
        port = FakePort()
        original = port.get_issue

        def changed(key):
            original(key)
            return {"fields": {"updated": "different"}}

        port.get_issue = changed
        plan = jira_port.Plan([jira_port.Operation("edit", {"key": "A", "fields": {}}, "t1")])
        outcome = jira_port.apply_plan(port, plan, self.log, "r", "REF:FEAT-001")
        self.assertEqual(outcome.error, "Conflict")
        self.assertEqual([call[0] for call in port.calls], ["get_issue"])
        self.assertEqual(writelog.read(self.log), [])

    def test_ambiguous_create_is_never_retried_and_reports_recovery(self):
        class Port(FakePort):
            def create_issue(self, fields):
                super().create_issue(fields)
                raise jira_port.Timeout()

        port = Port()
        port.found = [{"key": "PROJ-14"}]
        operation = jira_port.Operation(
            "create", {"fields": {"project": {"key": "PROJ"}, "labels": ["feat:FEAT-001"]}}
        )
        plan = jira_port.Plan([operation])
        outcome = jira_port.apply_plan(port, plan, self.log, "r", "REF:FEAT-001")
        self.assertEqual(outcome.status, "recovered")
        self.assertEqual([c[0] for c in port.calls], ["create", "search_by_label"])
        self.assertIn("ambiguous", self.log.read_text())
        self.assertEqual(len(writelog.read(self.log)), 2)

    def test_ambiguous_create_without_match_still_does_not_retry(self):
        class Port(FakePort):
            def create_issue(self, fields):
                super().create_issue(fields)
                raise jira_port.Timeout()

        port = Port()
        operation = jira_port.Operation(
            "create", {"fields": {"project": {"key": "PROJ"}, "labels": ["feat:FEAT-001"]}}
        )
        outcome = jira_port.apply_plan(
            port, jira_port.Plan([operation]), self.log, "r", "REF:FEAT-001"
        )
        self.assertEqual(outcome.status, "not-recovered")
        self.assertEqual([c[0] for c in port.calls], ["create", "search_by_label"])

    def test_rate_limited_write_stops_by_default(self):
        class Port(FakePort):
            def edit_issue(self, key, fields):
                raise jira_port.RateLimited(5)

        plan = jira_port.Plan([jira_port.Operation("edit", {"key": "A", "fields": {}}, "t1")])
        outcome = jira_port.apply_plan(Port(), plan, self.log, "r", "REF:FEAT-001")
        self.assertEqual(outcome.status, "stopped")
        self.assertEqual(outcome.error, "RateLimited")

    def test_plan_cli_prints_hashes_and_rejects_bad_json(self):
        data = {
            "operations": [
                {"kind": "edit", "payload": {"key": "A", "fields": {}}, "expect_updated": "t1"}
            ]
        }
        path = Path(self.tmp.name) / "plan.json"
        path.write_text(json.dumps(data))
        self.assertEqual(jira_port.main([str(path)]), 0)
        path.write_text("not json")
        self.assertEqual(jira_port.main([str(path)]), 2)


if __name__ == "__main__":
    unittest.main()
