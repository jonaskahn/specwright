"""A criterion written as `- **Given** …` bullets reads exactly like the plain three-line form."""

import importlib.util
import re
import sys
import unittest
from pathlib import Path

from kitlib import illustration

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sw-spec/scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export = load("export_feature")
card_gen = load("card_gen")
lint_spec = importlib.util.spec_from_file_location(
    "specwright_lint_layout", ROOT / "skills/_shared/scripts/sw_lint.py"
)
lint = importlib.util.module_from_spec(lint_spec)
sys.modules[lint_spec.name] = lint
lint_spec.loader.exec_module(lint)

FIXTURES = ROOT / "workshop/fixtures/lint"
DRAW = (FIXTURES / "illustration-draw.md").read_text()
GOOD = (FIXTURES / "good-story.md").read_text()


def bulleted(text: str) -> str:
    return re.sub(r"(?m)^(Given|When|Then|And|But)\b", r"- **\1**", text)


class LayoutTests(unittest.TestCase):
    def test_the_bulleted_form_differs_from_the_plain_one(self):
        self.assertIn("- **Given** ", bulleted(GOOD))
        self.assertNotEqual(bulleted(GOOD), GOOD)

    def test_the_illustration_count_does_not_change(self):
        self.assertEqual(
            illustration.count_signals(bulleted(DRAW)), illustration.count_signals(DRAW)
        )

    def test_the_gherkin_export_is_the_same(self):
        plain, _ = export.render(GOOD, "FEAT-001")
        fancy, _ = export.render(bulleted(GOOD), "FEAT-001")
        self.assertEqual(plain.split("\n", 1)[1], fancy.split("\n", 1)[1])
        self.assertIn("    Given ", fancy)
        self.assertNotIn("**", fancy)

    def test_an_and_step_is_exported_as_a_step(self):
        story = bulleted(GOOD).replace("- **Then**", "- **And** the owner is told\n- **Then**", 1)
        self.assertIn("    And the owner is told", export.render(story, "FEAT-001")[0])

    def findings(self, text):
        return lint.lint_document(
            lint.Doc.from_text("02-drafts/FEAT-001.story.md", text),
            lint.Context(
                Path("."), docs=[], gate="review", definitions=lint.definitions_for([], "REF")
            ),
        )

    def test_lint_still_finds_the_three_steps_in_order(self):
        for text in (GOOD, bulleted(GOOD)):
            self.assertNotIn("L-007", {f.rule for f in self.findings(text)})
        broken = bulleted(GOOD).replace("- **Given**", "- **Then**", 1)
        self.assertIn("L-007", {f.rule for f in self.findings(broken)})

    def test_a_card_may_not_repeat_a_bulleted_step(self):
        card = card_gen.generate(GOOD)
        card_gen.validate_card(card)
        with self.assertRaises(ValueError):
            card_gen.validate_card(card + "\n- **Given** a buyer\n")


if __name__ == "__main__":
    unittest.main()
