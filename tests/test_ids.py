import unittest

from kitlib import ids


class IdTests(unittest.TestCase):
    def test_parse_plain_and_qualified(self):
        self.assertEqual(ids.parse_ref("BR-001"), ids.Ref(None, "BR-001"))
        ref = ids.parse_ref("PRG:BR-001")
        self.assertEqual((ref.scope, ref.id, ref.qualified), ("PRG", "BR-001", "PRG:BR-001"))
        self.assertEqual(ids.parse_ref("ORD:AC-012-2").id, "AC-012-2")

    def test_rejects_malformed(self):
        for bad in ("BR-1", "br-001", "FEAT-0001", "NFR-r-001", "PROJ-14 ", "AC-1-1"):
            self.assertIsNone(ids.parse_ref(bad), bad)

    def test_find_refs_keeps_order_and_uniqueness(self):
        text = "See BR-001, REF:FEAT-002 and BR-001 again; NFR-REF-001; PROJ-14."
        found = [r.qualified for r in ids.find_refs(text)]
        self.assertEqual(found, ["BR-001", "REF:FEAT-002", "NFR-REF-001"])

    def test_type_patterns(self):
        self.assertTrue(ids.matches_type("feature", "FEAT-001"))
        self.assertTrue(ids.matches_type("nfr", "NFR-REF-001"))
        self.assertTrue(ids.matches_type("src", "SRC-0007"))
        self.assertFalse(ids.matches_type("src", "SRC-007"))
        self.assertFalse(ids.matches_type("unknown", "X-001"))

    def test_ac_helpers(self):
        self.assertEqual(ids.ac_id(1, 2), "AC-001-2")
        self.assertEqual(ids.parse_ac("AC-012-3"), (12, 3))
        self.assertIsNone(ids.parse_ac("FEAT-001"))
        self.assertEqual(ids.feat_number("FEAT-004"), 4)
        with self.assertRaises(ValueError):
            ids.feat_number("BR-001")

    def test_tombstones(self):
        self.assertEqual(
            ids.tombstones("~~AC-001-3~~ gone, ~~AC-002-1~~"), ["AC-001-3", "AC-002-1"]
        )

    def test_next_id_never_reuses_a_number(self):
        taken = ["BR-001", "BR-003", "REF:BR-004", "BO-009"]
        self.assertEqual(ids.next_id("BR", taken), "BR-005")
        self.assertEqual(ids.next_id("NFR-REF", ["NFR-REF-002"]), "NFR-REF-003")
        self.assertEqual(ids.next_id("SRC", [], width=4), "SRC-0001")

    def test_scope_and_prefix(self):
        self.assertTrue(ids.is_scope("REF"))
        self.assertFalse(ids.is_scope("ref"))
        self.assertFalse(ids.is_scope("TOOLONG"))
        self.assertEqual(ids.prefix_of("NFR-REF-001"), "NFR")


if __name__ == "__main__":
    unittest.main()
