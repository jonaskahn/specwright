"""A reserved feature keeps its name; an unanswered blocking question stops entry into review."""

import importlib.util
import subprocess
import sys
from pathlib import Path

from kitlib import blockers, frontmatter, lifecycle, rtm, schema
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "skills/sw-spec/scripts/new_story.py"
spec = importlib.util.spec_from_file_location("new_story_blockers", SCRIPT)
new_story = importlib.util.module_from_spec(spec)
spec.loader.exec_module(new_story)


class BlockerTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.draft.write_text(frontmatter.update(self.draft.read_text(), {"status": "draft"}))

    def question(self, ident="Q-001", **extra):
        fm = {
            "id": ident,
            "type": "q",
            "scope": "REF",
            "title": "Which window applies",
            "aliases": [],
            "status": "open",
            "affects": ["FEAT-001"],
        }
        fm.update(extra)
        (self.base / f"records/{ident}.md").write_text(frontmatter.render(fm, "# Q\n"))

    def reserve(self, ident="FEAT-002", **cells):
        values = {"Kind": "story", "Title": "Decide a refund", "State": "reserved"}
        values.update(cells)
        rtm.registry_upsert(self.base / "_meta/id-registry.md", f"REF:{ident}", values, "sw-shape")

    # ---- blocking questions

    def test_only_open_blocking_questions_that_name_the_feature_count(self):
        self.question("Q-001")
        self.question("Q-002", blocking=False)
        self.question("Q-003", status="answered")
        self.question("Q-004", affects=["FEAT-002"])
        self.question("Q-005", status="proposed")
        found = blockers.blocking_questions(self.base, "REF", "FEAT-001")
        self.assertEqual([q for q, _ in found], ["Q-001", "Q-005"])

    def test_submitting_for_review_is_refused_until_blocking_questions_are_answered(self):
        self.question()
        with self.assertRaisesRegex(ValueError, "blocking questions are unanswered: Q-001"):
            lifecycle.transition(self.base, "REF:FEAT-001", "submit-review")
        self.question(status="answered")
        preview = lifecycle.transition(self.base, "REF:FEAT-001", "submit-review")
        self.assertIn("confirm", preview)

    def test_a_non_blocking_question_does_not_stop_review(self):
        self.question(blocking=False)
        self.assertIn("confirm", lifecycle.transition(self.base, "REF:FEAT-001", "submit-review"))

    # ---- reserved features

    def test_a_reserved_feature_is_specified_under_its_own_id_title_and_aliases(self):
        self.reserve(Aliases="LEG-200|payout-flow")
        path = new_story.create(self.base, "REF", "", reserved="FEAT-002")
        self.assertEqual(path.name, "FEAT-002.story.md")
        fm = frontmatter.parse(path.read_text()).fm
        self.assertEqual(fm["title"], "Decide a refund")
        self.assertEqual(fm["aliases"], ["LEG-200", "payout-flow"])
        self.assertEqual(fm["id"], "FEAT-002")

    def test_only_a_live_reserved_feature_without_a_story_can_be_specified(self):
        self.reserve("FEAT-003", State="withdrawn")
        for bad in ("FEAT-009", "FEAT-001", "FEAT-003", "STORY-2"):
            with self.assertRaises(ValueError, msg=bad):
                new_story.create(self.base, "REF", "x", reserved=bad)

    def test_the_command_line_warns_about_blocking_questions_but_still_creates_the_draft(self):
        self.reserve()
        self.question("Q-001", affects=["FEAT-002"])
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--scope-root",
                str(self.base),
                "--scope",
                "REF",
                "--reserved",
                "FEAT-002",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.base / "02-drafts/FEAT-002.story.md").is_file())
        self.assertIn("blocking question Q-001 is open", result.stderr)
        none = subprocess.run(
            [sys.executable, str(SCRIPT), "--scope-root", str(self.base), "--scope", "REF"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(none.returncode, 1)
        self.assertEqual(schema.OPEN_Q, {"proposed", "candidate", "open"})
