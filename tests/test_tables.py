import unittest

from kitlib import tables

TEXT = """# RTM

Intro text.

| Spec ID | BO [sw-spec] | Jira [sw-publish] |
|---|---|---|
| REF:FEAT-001 | BO-001 | PROJ-14 |
| REF:FEAT-002 | BO-002 |

Trailing note.
"""


class TableTests(unittest.TestCase):
    def test_round_trip_keeps_surrounding_text(self):
        doc = tables.parse(TEXT)
        self.assertTrue(doc.before.endswith("Intro text.\n\n"))
        self.assertTrue(doc.after.endswith("Trailing note.\n"))
        again = tables.parse(doc.render())
        self.assertEqual(again.table.rows, doc.table.rows)
        self.assertEqual(again.after, doc.after)

    def test_short_rows_are_padded(self):
        self.assertEqual(tables.parse(TEXT).table.rows[1][2], tables.EMPTY)

    def test_upsert_sets_only_named_cells(self):
        table = tables.parse(TEXT).table
        self.assertFalse(table.upsert("REF:FEAT-001", {"Jira [sw-publish]": "PROJ-15"}))
        self.assertEqual(table.get("REF:FEAT-001", "BO [sw-spec]"), "BO-001")
        self.assertEqual(table.get("REF:FEAT-001", "Jira [sw-publish]"), "PROJ-15")

    def test_upsert_creates_missing_rows_with_placeholders(self):
        table = tables.parse(TEXT).table
        self.assertTrue(table.upsert("REF:FEAT-003", {"BO [sw-spec]": "BO-003"}))
        self.assertEqual(table.find("REF:FEAT-003"), ["REF:FEAT-003", "BO-003", tables.EMPTY])

    def test_pipes_in_cells_are_escaped(self):
        table = tables.Table(["Spec ID", "Note"])
        table.upsert("A", {"Note": "x | y"})
        parsed = tables.parse(table.render()).table
        self.assertEqual(parsed.get("A", "Note"), "x | y")

    def test_unknown_column_and_key_column_are_rejected(self):
        table = tables.parse(TEXT).table
        with self.assertRaises(tables.TableError):
            table.upsert("REF:FEAT-001", {"Nope": "x"})
        with self.assertRaises(tables.TableError):
            table.upsert("REF:FEAT-001", {"Spec ID": "other"})

    def test_overlong_row_is_rejected(self):
        with self.assertRaises(tables.TableError):
            tables.parse("| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")

    def test_text_without_a_table(self):
        doc = tables.parse("just text\n")
        self.assertIsNone(doc.table)
        self.assertEqual(doc.render(), "just text\n")


if __name__ == "__main__":
    unittest.main()
