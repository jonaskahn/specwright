import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from kitlib import writelog

NOW = datetime(2026, 11, 10, 3, 11, 58, tzinfo=timezone.utc)


class WriteLogTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "_meta" / "write-log.md"

    def test_intent_and_result_lines(self):
        writelog.intent(
            self.path, "7f3a", 1, "sw-publish", "create", "REF:FEAT-001", "jira:PROJ", now=NOW
        )
        writelog.result(self.path, "7f3a", 1, "ok", "PROJ-14", now=NOW)
        lines = self.path.read_text().splitlines()
        expected = (
            "2026-11-10T03:11:58Z | INTENT | run=7f3a | op=1 | sw-publish | create"
            " | REF:FEAT-001 | jira:PROJ"
        )
        self.assertEqual(lines[0], expected)
        self.assertEqual(lines[1], "2026-11-10T03:11:58Z | RESULT | run=7f3a | op=1 | ok | PROJ-14")

    def test_unfinished_reports_intents_without_result(self):
        writelog.intent(self.path, "a", 1, "sw-publish", "create", "X")
        writelog.result(self.path, "a", 1, "ok")
        writelog.intent(self.path, "a", 2, "sw-publish", "edit", "Y")
        pending = writelog.unfinished(self.path)
        self.assertEqual([(e.run, e.op) for e in pending], [("a", 2)])

    def test_log_is_append_only_across_calls(self):
        writelog.intent(self.path, "a", 1, "s", "x", "t")
        before = self.path.read_text()
        writelog.intent(self.path, "a", 2, "s", "x", "t")
        self.assertTrue(self.path.read_text().startswith(before))

    def test_separators_in_values_cannot_forge_lines(self):
        writelog.intent(self.path, "a", 1, "s", "x", "t | RESULT\nforged")
        self.assertEqual(len(self.path.read_text().splitlines()), 1)
        self.assertEqual(len(writelog.read(self.path)), 1)

    def test_missing_file_reads_as_empty(self):
        self.assertEqual(writelog.read(self.path), [])

    def test_headers_and_prose_are_skipped(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("# Write log\n\nnotes\n")
        self.assertEqual(writelog.read(self.path), [])

    def test_run_ids_are_short_hex(self):
        self.assertRegex(writelog.new_run_id(), r"^[0-9a-f]{4}$")


if __name__ == "__main__":
    unittest.main()
