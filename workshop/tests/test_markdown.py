import unittest

from kitlib import markdown

BODY = """\
## Goal
As a user.

## Acceptance criteria
### AC-001-1 — Full refund
Given a
When b
Then c

### AC-001-2 - Half refund
Given d
~~AC-001-3~~ withdrawn

## Out of scope
- x — reason: y
"""


class SectionTests(unittest.TestCase):
    def test_sections_by_heading(self):
        found = markdown.sections(BODY)
        self.assertEqual(list(found), ["Goal", "Acceptance criteria", "Out of scope"])
        self.assertEqual(found["Goal"].text, "As a user.")

    def test_line_numbers_respect_first_line(self):
        found = markdown.sections(BODY, first_line=10)
        self.assertEqual(found["Goal"].line, 10)

    def test_headings_inside_code_fences_are_ignored(self):
        body = "## A\n" + "\x60" * 3 + "\n## not a heading\n" + "\x60" * 3 + "\n## B\n"
        self.assertEqual(list(markdown.sections(body)), ["A", "B"])

    def test_first_duplicate_heading_wins(self):
        found = markdown.sections("## A\none\n## A\ntwo\n")
        self.assertEqual(found["A"].text, "one")

    def test_drop_section(self):
        out = markdown.drop_section(BODY, "Goal")
        self.assertNotIn("As a user", out)
        self.assertIn("## Acceptance criteria", out)

    def test_ac_blocks_and_tombstones(self):
        section = markdown.sections(BODY)["Acceptance criteria"]
        blocks = markdown.ac_blocks(section)
        self.assertEqual(list(blocks), ["AC-001-1", "AC-001-2"])
        self.assertEqual(blocks["AC-001-1"].title, "Full refund")
        self.assertIn("Then c", blocks["AC-001-1"].text)
        self.assertEqual(markdown.ac_tombstones(section), ["AC-001-3"])

    def test_missing_section_gives_empty_results(self):
        self.assertEqual(markdown.ac_blocks(None), {})
        self.assertEqual(markdown.ac_tombstones(None), [])

    def test_normalise(self):
        self.assertEqual(markdown.normalise("\r\na  \r\n\r\nb\t\n\n"), "a\n\nb")


if __name__ == "__main__":
    unittest.main()
