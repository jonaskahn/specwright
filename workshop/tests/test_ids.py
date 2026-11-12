import tempfile
import unittest
from pathlib import Path

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

    def test_asset_ids(self):
        self.assertTrue(ids.matches_type("asset", "ASSET-001"))
        self.assertFalse(ids.matches_type("asset", "ASSET-01"))
        self.assertEqual(ids.parse_ref("REF:ASSET-003").qualified, "REF:ASSET-003")

    def test_scope_and_prefix(self):
        self.assertTrue(ids.is_scope("REF"))
        self.assertFalse(ids.is_scope("ref"))
        self.assertFalse(ids.is_scope("TOOLONG"))
        self.assertEqual(ids.prefix_of("NFR-REF-001"), "NFR")


if __name__ == "__main__":
    unittest.main()


class NamingTests(unittest.TestCase):
    def test_slug_is_ascii_lowercase_and_bounded(self):
        self.assertEqual(ids.slugify("Reset password: e-mail link!"), "reset-password-e-mail-link")
        self.assertEqual(ids.slugify("Hoàn tiền đơn hàng"), "hoan-tien-on-hang")
        self.assertEqual(ids.slugify("???"), "")
        long = ids.slugify("word " * 40)
        self.assertLessEqual(len(long), ids.SLUG_MAX)
        self.assertFalse(long.endswith("-"))

    def test_filename_keeps_the_id_before_the_double_hyphen(self):
        self.assertEqual(
            ids.record_filename("FEAT-012", "Reset password"), "FEAT-012--reset-password.md"
        )
        self.assertEqual(ids.record_filename("Q-001", "???"), "Q-001.md")

    def test_id_is_read_back_from_every_name_form(self):
        for name in ("Q-001.md", "Q-001--why-so.md", "Q-001", "records/Q-001--x.md"):
            self.assertEqual(ids.id_from_name(name), "Q-001", name)
        self.assertEqual(ids.id_from_name("FEAT-001.story.md"), "FEAT-001")
        self.assertEqual(ids.id_from_name("SRC-0007--po-email.md"), "SRC-0007")
        self.assertIsNone(ids.id_from_name("notes.md"))
        self.assertIsNone(ids.id_from_name("Q-0011.md"))

    def test_find_record_accepts_plain_and_slugged_names(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            (folder / "Q-001.md").write_text("a")
            (folder / "Q-002--later.md").write_text("b")
            self.assertEqual(ids.find_record(folder, "Q-001").name, "Q-001.md")
            self.assertEqual(ids.find_record(folder, "Q-002").name, "Q-002--later.md")
            self.assertIsNone(ids.find_record(folder, "Q-003"))
            self.assertIsNone(ids.find_record(folder / "missing", "Q-001"))

    def test_taken_ids_include_names_text_and_tombstones(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            (base / "records").mkdir()
            (base / "records/Q-004--old.md").write_text("withdrawn\n")
            (base / "_meta").mkdir()
            (base / "_meta/id-registry.md").write_text("| REF:FEAT-009 |\n")
            (base / "02-drafts").mkdir()
            (base / "02-drafts/FEAT-001.story.md").write_text("~~AC-001-3~~ and DEC-007\n")
            (base / "00-inbox/raw").mkdir(parents=True)
            (base / "00-inbox/raw/ignored.md").write_text("Q-999\n")
            taken = ids.taken_ids(base)
            for wanted in ("Q-004", "FEAT-009", "FEAT-001", "AC-001-3", "DEC-007"):
                self.assertIn(wanted, taken)
            self.assertNotIn("Q-999", taken)
            self.assertEqual(ids.next_id("Q", taken), "Q-005")
            self.assertEqual(ids.next_id("DEC", taken), "DEC-008")
