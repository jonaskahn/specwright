"""Index-only pages are told apart from real content so they never count as settled evidence."""

import unittest

from kitlib import snapshots


class ContentClassTests(unittest.TestCase):
    def test_a_page_of_headings_and_links_is_index_only(self):
        text = (
            "# Refunds space\n\n## Pages\n\n- [Eligibility](https://w.test/1)\n"
            "- [Window](https://w.test/2)\n\n{children}\n"
        )
        self.assertEqual(snapshots.content_class(text), "index-only")

    def test_a_bare_heading_and_nothing_else_is_index_only(self):
        self.assertEqual(snapshots.content_class("# Parent page\n"), "index-only")

    def test_converted_child_titles_without_markup_are_index_only(self):
        self.assertEqual(
            snapshots.content_class("Refund space home\nEligibility\nPayout\n"), "index-only"
        )
        self.assertEqual(snapshots.content_class("Refunds close after 14 days\n"), "content")
        self.assertEqual(
            snapshots.content_class("Refund window\nRefunds close after 14 days.\n"), "content"
        )

    def test_no_text_at_all_is_empty(self):
        self.assertEqual(snapshots.content_class(""), "empty")
        self.assertEqual(snapshots.content_class("\n\n   \n"), "empty")

    def test_prose_makes_it_content_even_with_links(self):
        prose = " ".join(["Refunds are accepted for delivered orders within fourteen days."] * 3)
        text = f"# Policy\n\n{prose}\n\n- [Details](https://w.test/3)\n"
        self.assertEqual(snapshots.content_class(text), "content")

    def test_a_short_real_sentence_without_structure_is_content(self):
        self.assertEqual(snapshots.content_class("Refunds close after 14 days."), "content")

    def test_link_text_inside_prose_counts_as_words(self):
        link = "[the full refund eligibility rules for every product category](https://w.test/9)"
        tail = "before approving any request from a customer or an agent in any region."
        text = f"# Rules\n\nSee {link} {tail}\n"
        self.assertEqual(snapshots.content_class(text), "content")

    def test_redaction_markers_are_counted(self):
        self.assertEqual(snapshots.redaction_markers("a [REDACTED:email] b [REDACTED:card]"), 2)
        self.assertEqual(snapshots.redaction_markers("nothing"), 0)


if __name__ == "__main__":
    unittest.main()
