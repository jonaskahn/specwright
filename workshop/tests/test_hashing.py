import unittest

from kitlib import hashing

BASE = "---\nid: FEAT-001\nstatus: draft\n---\n## Goal\nText\n\n## Identity\nDraft hash: x\n"


class HashTests(unittest.TestCase):
    def test_identity_section_does_not_change_the_hash(self):
        other = BASE.replace("Draft hash: x", "Draft hash: completely different")
        self.assertEqual(hashing.draft_hash(BASE), hashing.draft_hash(other))

    def test_front_matter_changes_do_not_change_the_hash(self):
        self.assertEqual(
            hashing.draft_hash(BASE), hashing.draft_hash(BASE.replace("draft", "in-review"))
        )

    def test_whitespace_noise_is_ignored(self):
        noisy = BASE.replace("Text\n", "Text   \r\n")
        self.assertEqual(hashing.draft_hash(BASE), hashing.draft_hash(noisy))

    def test_content_change_changes_the_hash(self):
        self.assertNotEqual(
            hashing.draft_hash(BASE), hashing.draft_hash(BASE.replace("Text", "Other"))
        )

    def test_format_and_short(self):
        value = hashing.draft_hash(BASE)
        self.assertRegex(value, r"^sha256:[0-9a-f]{64}$")
        self.assertEqual(hashing.short(value), value[7:19])
        self.assertEqual(len(hashing.bytes_hash(b"x")), 64)

    def test_stamp_replaces_the_recorded_hash_and_is_idempotent(self):
        stale = BASE.replace(
            "Draft hash: x",
            "Draft hash: sha256:0000000000000000000000000000000000000000000000000000000000000000",
        )
        stamped = hashing.stamp(stale)
        self.assertIn(f"Draft hash: {hashing.draft_hash(BASE)}", stamped)
        self.assertNotIn("00000000", stamped)
        self.assertEqual(hashing.stamp(stamped), stamped)  # a second stamp is a no-op
        self.assertFalse(hashing.needs_stamp(stamped))
        self.assertTrue(hashing.needs_stamp(stale))

    def test_stamp_does_not_change_the_hash(self):
        stale = BASE.replace("Draft hash: x", "Draft hash: nope")
        self.assertEqual(hashing.draft_hash(stale), hashing.draft_hash(hashing.stamp(stale)))


if __name__ == "__main__":
    unittest.main()
