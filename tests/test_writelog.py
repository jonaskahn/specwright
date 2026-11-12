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


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.base = Path(self.dir.name)
        (self.base / "_meta").mkdir()
        (self.base / "records").mkdir()
        self.log = self.base / "_meta/write-log.md"

    def test_an_operation_logs_intent_then_ok_with_file_hashes(self):
        note = self.base / "records/Q-001.md"
        with writelog.operation(self.log, "sw-shape", "q-new", "REF:Q-001") as op:
            note.write_text("question\n")
            op.wrote(note)
        entries = writelog.read(self.log)
        self.assertEqual([e.kind for e in entries], ["INTENT", "RESULT"])
        self.assertEqual(entries[0].fields[:3], ["sw-shape", "q-new", "REF:Q-001"])
        self.assertEqual(entries[1].fields[0], "ok")
        self.assertEqual(entries[1].fields[1], f"file=records/Q-001.md@{writelog.file_hash(note)}")
        self.assertEqual(writelog.unfinished(self.log), [])

    def test_a_failure_is_logged_as_an_error_and_reraised(self):
        with (
            self.assertRaises(RuntimeError),
            writelog.operation(self.log, "sw-shape", "q-new", "X"),
        ):
            raise RuntimeError("disk full")
        entries = writelog.read(self.log)
        self.assertEqual(entries[-1].fields[:2], ["error", "RuntimeError"])
        self.assertEqual(writelog.unfinished(self.log), [])

    def test_only_remote_uncertainty_needs_recovery(self):
        with (
            self.assertRaises(RuntimeError),
            writelog.operation(self.log, "sw-shape", "q-new", "X"),
        ):
            raise RuntimeError("local failure")
        self.assertEqual(writelog.uncertain(self.log), [])
        writelog.intent(self.log, "ab12", 1, "sw-publish", "create", "REF:FEAT-001")
        self.assertEqual(len(writelog.uncertain(self.log)), 1)
        writelog.result(self.log, "ab12", 1, "error", "timeout")
        self.assertEqual(len(writelog.uncertain(self.log)), 1)

    def test_drift_names_files_edited_after_their_last_logged_write(self):
        note = self.base / "records/Q-001.md"
        other = self.base / "records/Q-002.md"
        other.write_text("never logged\n")
        with writelog.operation(self.log, "sw-shape", "q-new", "REF:Q-001") as op:
            note.write_text("v1\n")
            op.wrote(note)
        self.assertEqual(writelog.drift(self.log), [])
        note.write_text("edited by hand\n")
        other.write_text("also edited\n")
        self.assertEqual(
            writelog.drift(self.log), ["records/Q-001.md changed outside a logged write"]
        )
        with writelog.operation(self.log, "sw-shape", "q-answer", "REF:Q-001") as op:
            op.wrote(note)
        self.assertEqual(writelog.drift(self.log), [])
        note.unlink()
        self.assertEqual(
            writelog.drift(self.log), ["records/Q-001.md is gone since its last logged write"]
        )

    def test_shared_state_and_worker_files_are_not_judged(self):
        (self.base / "01-analysis/candidates").mkdir(parents=True)
        files = [
            self.base / "_meta/id-registry.md",
            self.base / "01-analysis/candidates/CAND-001--x.md",
        ]
        with writelog.operation(self.log, "sw-shape", "x", "X") as op:
            for f in files:
                f.write_text("one\n")
                op.wrote(f)
        for f in files:
            f.write_text("two\n")
        self.assertEqual(writelog.drift(self.log), [])

    def test_line_ending_conversion_is_not_drift(self):
        note = self.base / "records/Q-001.md"
        with writelog.operation(self.log, "sw-shape", "q-new", "X") as op:
            note.write_bytes(b"a\nb\n")
            op.wrote(note)
        note.write_bytes(b"a\r\nb\r\n")
        self.assertEqual(writelog.drift(self.log), [])


if __name__ == "__main__":
    unittest.main()
