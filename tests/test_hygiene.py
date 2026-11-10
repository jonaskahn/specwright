import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "hygiene", Path(__file__).resolve().parent.parent / "tools" / "hygiene.py"
)
hygiene = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(hygiene)


class HygieneTests(unittest.TestCase):
    # Offending samples are assembled at runtime so this file passes the check it tests.
    LABELS = ["done in " + "phase " + "2", "ta" + "sk-14", "see m" + "-001", "wa" + "ve 3 agents"]
    BRIEF = "see specwright-kit" + "-v1.2.md"

    def problems(self, text, patterns=None):
        return hygiene.scan(text, patterns or hygiene.CONTENT_PATTERNS, "x")

    def test_flags_work_tracking_labels(self):
        for bad in [*self.LABELS, "p" + "-12 done"]:
            self.assertTrue(self.problems(bad), bad)

    def test_allows_product_identifiers(self):
        for good in ("L-024 fires", "FEAT-001 and AC-001-2", "BR-001", "a step-by-step guide"):
            self.assertFalse(self.problems(good), good)

    def test_flags_the_brief_file_name(self):
        self.assertTrue(self.problems(self.BRIEF))

    def test_commit_messages_reject_trailers(self):
        msg = "Add parser\n\nCo-authored-by: someone <a@b.c>\n"
        self.assertTrue(self.problems(msg, hygiene.MESSAGE_PATTERNS))
        self.assertTrue(self.problems("Generated with a tool", hygiene.MESSAGE_PATTERNS))
        self.assertFalse(self.problems("Add parser for front matter", hygiene.MESSAGE_PATTERNS))


if __name__ == "__main__":
    unittest.main()
