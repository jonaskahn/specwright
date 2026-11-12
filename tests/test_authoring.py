"""Offline checks for idea wording, card generation and story allocation."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


leakage = load("leakage", SCRIPTS / "sw-shape/scripts/leakage.py")
card_gen = load("card_gen", SCRIPTS / "sw-spec/scripts/card_gen.py")
new_story = load("new_story", SCRIPTS / "sw-spec/scripts/new_story.py")

BEFORE = """---
id: IDEA-refunds
type: idea
scope: REF
status: draft
---
## Problem
Customers need a big green button that calls the payments API.

## Smallest valuable outcome
Customers get approval through a React screen.
"""

AFTER = """---
id: IDEA-refunds
type: idea
scope: REF
status: draft
---
## Problem
Customers cannot request a refund without contacting support; handling takes 3 days.

## Smallest valuable outcome
Customers submit a refund request and receive a recorded decision.
"""


class LeakageTests(unittest.TestCase):
    def test_implementation_words_are_reported_with_file_lines(self):
        words = leakage.load_words()
        findings = leakage.check(BEFORE, words)
        self.assertTrue(findings)
        self.assertTrue(any("green button" in str(item) for item in findings))

    def test_problem_led_brief_is_clean(self):
        self.assertEqual(leakage.check(AFTER, leakage.load_words()), [])

    def test_missing_sections_fail_closed(self):
        with self.assertRaises(ValueError):
            leakage.check("## Problem\nCustomers wait.\n", ["green button"])

    def test_coverage_names_what_was_scanned_and_what_was_not(self):
        brief = (
            "## Actors\nA clerk uses a green button today.\n\n## Problem\nCustomers wait.\n\n"
            "## Smallest valuable outcome\nThey get a result.\n\n"
            "## Assumptions\nA green button helps.\n"
        )
        words = ["green button"]
        found, scanned, skipped = leakage.scan(brief, words)
        self.assertEqual(found, [])  # a clean scan, yet design words sit in other sections
        self.assertEqual(scanned, ["Problem", "Smallest valuable outcome"])
        self.assertEqual(skipped, ["Actors", "Assumptions"])
        found, scanned, skipped = leakage.scan(brief, words, also=("assumptions",))
        self.assertEqual([word for _, word in found], ["green button"])
        self.assertEqual(skipped, ["Actors"])


class CardTests(unittest.TestCase):
    def story(self):
        return (ROOT / "fixtures/refund/story/FEAT-001.story.md").read_text()

    def test_generated_card_is_deterministic_and_within_limits(self):
        first = card_gen.generate(self.story())
        self.assertEqual(first, card_gen.generate(self.story()))
        card_gen.validate_card(first)
        self.assertLessEqual(len(first.splitlines()), 80)

    def test_cards_never_carry_acceptance_criteria(self):
        text = card_gen.generate(self.story())
        self.assertNotIn("Given ", text)
        self.assertNotIn("AC-001-1", text)

    def test_invalid_story_sections_are_rejected(self):
        with self.assertRaises(ValueError):
            card_gen.generate(self.story().replace("## Business rules", "## Other"))


class StoryAllocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_next_feature_is_allocated_from_historical_ids(self):
        (self.root / "02-drafts").mkdir()
        (self.root / "02-drafts" / "FEAT-001.story.md").write_text("id: FEAT-001\n")
        created = new_story.create(self.root, "REF", "Notify customer", feature="FEAT-002")
        self.assertEqual(created.name, "FEAT-002.story.md")
        self.assertTrue(created.is_file())

    def test_existing_file_is_not_overwritten(self):
        new_story.create(self.root, "REF", "Request a refund")
        with self.assertRaises(ValueError):
            new_story.create(self.root, "REF", "Request a refund", feature="FEAT-001")

    def test_invalid_scope_and_summary_are_rejected(self):
        with self.assertRaises(ValueError):
            new_story.create(self.root, "ref", "Request a refund")
        with self.assertRaises(ValueError):
            new_story.create(self.root, "REF", "x" * 101)

    def test_help_is_available(self):
        for script in (
            SCRIPTS / "sw-shape/scripts/leakage.py",
            SCRIPTS / "sw-spec/scripts/card_gen.py",
            SCRIPTS / "sw-spec/scripts/new_story.py",
        ):
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            self.assertIn("usage", result.stdout.lower())


class TemplateTests(unittest.TestCase):
    def test_story_template_sections_match_the_library(self):
        from kitlib import frontmatter, markdown, schema

        text = (ROOT / "skills/sw-spec/assets/jira-story.md").read_text()
        fm, body = frontmatter.split(text)
        self.assertEqual(fm["type"], "feature")
        self.assertEqual([s.name for s in markdown.iter_sections(body)], schema.STORY_SECTIONS)

    def test_card_template_is_compact(self):
        text = (ROOT / "skills/sw-spec/assets/summary-card.md").read_text()
        self.assertLessEqual(len(text.splitlines()), 80)


if __name__ == "__main__":
    unittest.main()
