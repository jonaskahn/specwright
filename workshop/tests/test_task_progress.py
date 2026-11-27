"""Per-task progress drives the story condition: accepted, in development, then done."""

from kitlib import frontmatter, hashing, lifecycle, markdown, schema, task_validation
from tests.test_workflow import WorkflowTestCase

TASKS = (
    "### TASK-001-1 — [backend] Record a refund\n"
    "Status: {one}\n"
    "Traces to: AC-001-1\n"
    "Touches: src/refunds/request.py\n"
    "Done when: one pending request exists\n"
    "{evidence_one}\n"
    "### TASK-001-2 — [backend] Refuse a late refund\n"
    "Status: {two}\n"
    "Traces to: AC-001-2\n"
    "Done when: a late request is refused\n"
    "{evidence_two}\n"
)


class TaskProgressTests(WorkflowTestCase):
    signoff = "optional"

    def tasks(self, one="not-started", two="not-started", evidence_one="", evidence_two=""):
        body = TASKS.format(one=one, two=two, evidence_one=evidence_one, evidence_two=evidence_two)
        path = self.base / "03-plan" / "FEAT-001.tasks.md"
        path.write_text(
            frontmatter.render(
                {
                    "feat": "FEAT-001",
                    "status": "ready",
                    "spec_hash": hashing.draft_hash(self.draft.read_text()),
                },
                body,
            )
        )
        return path

    def accepted(self, status="ready-to-publish"):
        """Put the draft in an accepted status with a sign-offs entry bound to its body hash."""
        text = self.draft.read_text()
        head, sep, body = text.partition("\n---\n")
        head = __import__("re").sub(r"^status:.*$", f"status: {status}", head, count=1, flags=8)
        # The draft hash covers the body only, so a front matter line never invalidates itself.
        digest = hashing.short(hashing.draft_hash(text))
        head = (
            head.rstrip("\n") + f"\nsignoffs:\n  - self | accept | sha256:{digest} | 2026-01-01\n"
        )
        self.draft.write_text(head + sep + body)

    def condition(self):
        return lifecycle.feature(self.base, "REF:FEAT-001")["condition"]

    def test_a_task_without_a_status_reads_as_not_started(self):
        block = markdown.task_blocks(
            "### TASK-001-1 — [backend] No status line\nTraces to: AC-001-1\n"
        )["TASK-001-1"]
        self.assertEqual(markdown.task_progress(block), markdown.DEFAULT_PROGRESS)
        self.assertEqual(markdown.DEFAULT_PROGRESS, "not-started")

    def test_an_unknown_status_word_falls_back_instead_of_breaking_the_board(self):
        block = markdown.task_blocks(
            "### TASK-001-1 — [backend] Odd status\nStatus: halfway\nTraces to: AC-001-1\n"
        )["TASK-001-1"]
        self.assertEqual(markdown.task_progress(block), "not-started")

    def test_the_new_statuses_are_valid_for_a_feature(self):
        for status in ("in-development", "done"):
            self.assertIn(status, schema.STATUSES["feature"])

    def test_a_finished_story_is_complete_even_without_a_plan_file(self):
        self.accepted("done")
        self.tasks(
            one="done",
            two="done",
            evidence_one="Evidence: make test -> 42",
            evidence_two="Evidence: make test -> 42",
        )
        row = lifecycle.feature(self.base, "REF:FEAT-001")
        self.assertEqual((row["station"], row["condition"]), ("plan", "complete"))

    def test_an_in_development_story_is_never_reported_complete(self):
        self.accepted("in-development")
        self.tasks(
            one="done",
            two="done",
            evidence_one="Evidence: make test",
            evidence_two="Evidence: make test",
        )
        self.assertEqual(self.condition(), "in-progress")

    def test_done_requires_evidence_on_every_covered_task(self):
        self.accepted()
        path = self.tasks(one="done", two="done")
        findings = task_validation.check(self.base, "FEAT-001")[1]
        self.assertTrue(any("Evidence" in f for f in findings))
        self.tasks(
            one="done",
            two="done",
            evidence_one="Evidence: 42 passed",
            evidence_two="Evidence: 45 passed",
        )
        self.assertEqual(task_validation.check(self.base, "FEAT-001")[1], [])
        self.assertTrue(path.is_file())
