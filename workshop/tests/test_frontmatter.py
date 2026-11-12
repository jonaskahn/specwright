import unittest

from kitlib import frontmatter

DOC = "---\nid: FEAT-001\nstatus: draft\n---\n## Goal\ntext\n"


class FrontMatterTests(unittest.TestCase):
    def test_splits_block_and_body(self):
        fm, body = frontmatter.split(DOC)
        self.assertEqual(fm, {"id": "FEAT-001", "status": "draft"})
        self.assertEqual(body, "## Goal\ntext\n")

    def test_body_line_points_at_first_body_line(self):
        self.assertEqual(frontmatter.parse(DOC).body_line, 5)

    def test_document_without_block(self):
        parsed = frontmatter.parse("# Title\n")
        self.assertIsNone(parsed.fm)
        self.assertIsNone(parsed.error)
        self.assertEqual(parsed.body, "# Title\n")

    def test_unclosed_block_is_an_error(self):
        parsed = frontmatter.parse("---\nid: X\n# no end\n")
        self.assertIsNone(parsed.fm)
        self.assertIn("not closed", parsed.error)

    def test_malformed_yaml_is_reported_not_raised(self):
        parsed = frontmatter.parse("---\nid: [1,\n---\nbody\n")
        self.assertIsNone(parsed.fm)
        self.assertIn("front matter", parsed.error)
        with self.assertRaises(frontmatter.FrontMatterError):
            frontmatter.split("---\nid: [1,\n---\nbody\n")

    def test_update_keeps_body_and_key_order(self):
        out = frontmatter.update(DOC, {"status": "in-review", "bo": ["BO-001"]})
        fm, body = frontmatter.split(out)
        self.assertEqual(list(fm), ["id", "status", "bo"])
        self.assertEqual(fm["status"], "in-review")
        self.assertEqual(body, "## Goal\ntext\n")

    def test_update_without_block_fails(self):
        with self.assertRaises(frontmatter.FrontMatterError):
            frontmatter.update("no block\n", {"a": 1})

    def test_byte_order_mark_is_ignored(self):
        self.assertEqual(frontmatter.parse("\ufeff" + DOC).fm["id"], "FEAT-001")


if __name__ == "__main__":
    unittest.main()
