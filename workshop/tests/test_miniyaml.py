import unittest

from kitlib import miniyaml

SAMPLE = """\
id: FEAT-001                 # required
type: feature
card: true
links: [https://example.atlassian.net/browse/PROJ-14]
linked_version: "jira:PROJ-14@2026-11-10T03:12:00Z"
bo: [BO-001, BO-002]
empty:
signoffs:
  - "PO | Lan Nguyen | 2026-11-10 | https://example.atlassian.net/c/1"
approvers:
  - role: PO
    name: Lan Nguyen
  - role: BA
    name: Jonas
publish:
  transitions: false
  limit: 50
"""


class ParseTests(unittest.TestCase):
    def test_reads_the_documented_subset(self):
        data = miniyaml.loads(SAMPLE)
        self.assertEqual(data["id"], "FEAT-001")
        self.assertIs(data["card"], True)
        self.assertEqual(data["links"], ["https://example.atlassian.net/browse/PROJ-14"])
        self.assertEqual(data["linked_version"], "jira:PROJ-14@2026-11-10T03:12:00Z")
        self.assertEqual(data["bo"], ["BO-001", "BO-002"])
        self.assertIsNone(data["empty"])
        self.assertEqual(len(data["signoffs"]), 1)
        self.assertEqual(data["approvers"][1], {"role": "BA", "name": "Jonas"})
        self.assertEqual(data["publish"], {"transitions": False, "limit": 50})

    def test_dates_stay_strings(self):
        self.assertEqual(miniyaml.loads("updated: 2026-11-10")["updated"], "2026-11-10")

    def test_quoted_values_keep_special_characters(self):
        data = miniyaml.loads("a: 'it''s # fine'\nb: \"x: y\"\n")
        self.assertEqual(data, {"a": "it's # fine", "b": "x: y"})

    def test_comment_inside_quotes_is_kept(self):
        self.assertEqual(miniyaml.loads('a: "x # y"')["a"], "x # y")

    def test_empty_document_is_an_empty_map(self):
        self.assertEqual(miniyaml.loads("# only a comment\n"), {})


class RejectTests(unittest.TestCase):
    def assert_rejected(self, text, fragment):
        with self.assertRaises(miniyaml.YamlError) as ctx:
            miniyaml.loads(text)
        self.assertIn(fragment, str(ctx.exception))

    def test_tab_indentation(self):
        self.assert_rejected("a:\n\tb: 1\n", "tab")

    def test_duplicate_keys(self):
        self.assert_rejected("a: 1\na: 2\n", "duplicate key 'a'")

    def test_anchors_and_block_scalars(self):
        self.assert_rejected("a: &x 1\n", "unsupported")
        self.assert_rejected("a: |\n  text\n", "unsupported")

    def test_nested_flow_collections(self):
        self.assert_rejected("a: [[1], 2]\n", "nested flow")
        self.assert_rejected("a: {b: 1}\n", "flow maps")

    def test_unterminated_flow_list_and_quote(self):
        self.assert_rejected("a: [1, 2\n", "unterminated")
        self.assert_rejected('a: "oops\n', "invalid double-quoted")

    def test_error_reports_the_line(self):
        with self.assertRaises(miniyaml.YamlError) as ctx:
            miniyaml.loads("a: 1\nb: [1,\n")
        self.assertEqual(ctx.exception.line, 2)

    def test_top_level_list(self):
        self.assert_rejected("- a\n- b\n", "top level")


class RoundTripTests(unittest.TestCase):
    def test_dump_then_load_is_identity(self):
        data = {
            "id": "FEAT-001",
            "flag": True,
            "none": None,
            "count": 7,
            "text": "needs: quoting",
            "word": "true",
            "digits": "123",
            "tags": ["a", "b, c", "d"],
            "nested": {"x": 1, "y": {"z": "deep"}},
            "people": [{"role": "PO", "name": "Lan"}, {"role": "BA", "name": "Jonas"}],
            "empty_list": [],
            "empty_map": {},
            "long": [f"https://example.com/item/{i}" for i in range(6)],
        }
        self.assertEqual(miniyaml.loads(miniyaml.dumps(data)), data)

    def test_strings_that_look_like_other_types_are_quoted(self):
        out = miniyaml.dumps({"a": "null", "b": "42", "c": "#x", "d": ""})
        self.assertEqual(miniyaml.loads(out), {"a": "null", "b": "42", "c": "#x", "d": ""})

    def test_non_map_and_bad_keys_are_rejected(self):
        with self.assertRaises(TypeError):
            miniyaml.dumps([1])
        with self.assertRaises(TypeError):
            miniyaml.dumps({"bad key": 1})


if __name__ == "__main__":
    unittest.main()
