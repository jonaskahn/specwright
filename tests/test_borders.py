import unittest

from kitlib import borders


class BorderTests(unittest.TestCase):
    def lines(self, text):
        return [line for line, _ in borders.find_one_sided(text)]

    def test_flags_lone_side_border_in_a_rule(self):
        self.assertEqual(self.lines(".a {\n  border-left: 4px solid red;\n}"), [2])

    def test_flags_inline_style_attributes(self):
        self.assertEqual(self.lines('<div style="border-bottom:1px solid #ccc">'), [1])

    def test_flags_logical_sides(self):
        for prop in ("border-inline-start", "border-block-end", "border-inline", "border-block"):
            self.assertTrue(self.lines(f".a {{ {prop}: 2px solid red; }}"), prop)

    def test_full_border_next_to_it_is_allowed(self):
        self.assertEqual(
            self.lines(".a { border: 1px solid #ccc; border-left: 4px solid red; }"), []
        )

    def test_none_and_zero_are_allowed(self):
        self.assertEqual(
            self.lines(".a { border-top: none; border-left: 0; border-right: 0px; }"), []
        )

    def test_box_shadow_and_outline_are_allowed(self):
        self.assertEqual(
            self.lines(".a { box-shadow: inset 4px 0 0 red; outline: 1px solid red; }"), []
        )

    def test_separate_rules_are_judged_separately(self):
        text = ".a { border: 1px solid red; }\n.b { border-top: 1px solid red; }"
        self.assertEqual(self.lines(text), [2])

    def test_message_includes_a_fix_hint(self):
        self.assertIn("box-shadow", borders.find_one_sided(".a{border-left:1px solid red}")[0][1])


if __name__ == "__main__":
    unittest.main()
