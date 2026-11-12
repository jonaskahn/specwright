"""Candidate extraction is assigned, checked and reviewed by program, one writer per file."""

import subprocess
import sys
from pathlib import Path

from kitlib import candidates, cite, frontmatter, recordops, tables, writelog
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "skills/sw-ingest/scripts/candidates.py"


class CandidateTests(WorkflowTestCase):
    def snapshot(self, ident, title, words=30, **extra):
        fm = {"id": ident, "type": "snapshot", "status": "raw", "title": title, "aliases": []}
        fm.update(extra)
        body = "Refunds close after 14 days.\n" + " ".join(["word"] * words) + "\n"
        (self.base / f"00-inbox/{ident}.md").write_text(frontmatter.render(fm, body))

    def setUp(self):
        super().setUp()
        self.snapshot("SRC-0001", "Alpha refunds")
        self.snapshot("SRC-0002", "Eligibility", source_parent="SRC-0001")
        self.snapshot("SRC-0003", "Payments home", labels=["payments"])
        self.snapshot("SRC-0004", "Zeta note")
        self.date = "2026-11-12"

    def assign(self, target=18000):
        rows, files = candidates.plan_assignment(self.base, "REF", target, self.date)
        existing = bool(candidates.read_assignment(self.base))
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        target_path = candidates.folder(self.base) / candidates.ASSIGNMENT
        previous = target_path.read_text() if existing else ""
        target_path.write_text(previous + candidates.assignment_text(rows, existing))
        return rows

    def w(self, src):
        """The worker a snapshot was assigned to."""
        return next(
            r["worker"] for r in candidates.read_assignment(self.base) if r["snapshot"] == src
        )

    def worker_path(self, ident):
        return next(candidates.folder(self.base).glob(f"{ident}--*.md"))

    def fill(self, ident, rows):
        """Write a worker's table; rows are (kind, topic, claim, citation, status, note)."""
        path = self.worker_path(ident)
        parsed = frontmatter.parse(path.read_text())
        table = tables.Table(list(candidates.HEADER))
        for n, (kind, topic, claim, citation, status, note) in enumerate(rows, 1):
            table.rows.append([str(n), kind, topic, claim, citation, status, note or tables.EMPTY])
        fm = dict(parsed.fm)
        fm["count"] = len(rows)
        body = parsed.body.split("## Candidates")[0] + "## Candidates\n\n" + table.render()
        path.write_text(frontmatter.render(fm, body))

    def stamp(self, source, line=8):
        return cite.stamp(cite.Sources(self.base), cite.parse_one(f"{source}:L{line}"))

    # ---- assignment

    def test_snapshots_are_grouped_by_root_page_label_or_general(self):
        rows = self.assign()
        by_snapshot = {r["snapshot"]: (r["worker"], r["area"]) for r in rows}
        self.assertEqual(by_snapshot["SRC-0001"][1], by_snapshot["SRC-0002"][1])
        self.assertEqual(by_snapshot["SRC-0001"][0], by_snapshot["SRC-0002"][0])
        self.assertEqual(by_snapshot["SRC-0003"][1], "payments")
        self.assertEqual(by_snapshot["SRC-0004"][1], "zeta-note")
        self.assertEqual(len({r["worker"] for r in rows}), 3)

    def test_a_large_area_is_split_so_no_worker_exceeds_the_target(self):
        for n in range(5, 8):
            self.snapshot(f"SRC-000{n}", f"Page {n}", words=600, source_parent="SRC-0001")
        rows = self.assign(target=1000)
        refund = [r for r in rows if r["area"].startswith("alpha-refunds")]
        per_worker: dict[str, int] = {}
        for r in refund:
            per_worker[r["worker"]] = per_worker.get(r["worker"], 0) + int(r["words"])
        self.assertGreater(len(per_worker), 1)
        self.assertTrue(all(total <= 1000 + 700 for total in per_worker.values()))
        self.assertEqual(sorted(r["area"] for r in refund)[0][:13], "alpha-refunds")

    def test_a_second_run_assigns_only_what_is_new(self):
        self.assign()
        self.assertEqual(self.assign(), [])
        self.snapshot("SRC-0005", "Late page")
        rows = self.assign()
        self.assertEqual([r["snapshot"] for r in rows], ["SRC-0005"])
        self.assertEqual(rows[0]["worker"], "CAND-004")
        self.assertEqual(candidates.check(self.base)[:1], [])

    def test_a_skeleton_is_a_valid_worker_file_with_nothing_unassigned(self):
        self.assign()
        self.assertEqual(candidates.check(self.base), [])
        fm = frontmatter.parse(self.worker_path("CAND-001").read_text()).fm
        self.assertEqual((fm["type"], fm["status"], fm["count"]), ("candidates", "raw", 0))

    # ---- check

    def test_a_filled_worker_file_passes(self):
        self.assign()
        cited = self.stamp("SRC-0001")
        self.fill(
            "CAND-001", [("rule", "refund window", "Refunds close after 14 days", cited, "raw", "")]
        )
        self.assertEqual(candidates.check(self.base), [])
        item = candidates.item(self.base, "CAND-001.1")
        self.assertEqual(
            (item.key, item.topic, item.citations), ("CAND-001.1", "refund window", [cited])
        )

    def test_coverage_gaps_and_double_assignment_are_found(self):
        self.assign()
        self.snapshot("SRC-0009", "Forgotten page")
        self.assertIn("SRC-0009: not assigned to any worker", candidates.check(self.base))
        path = candidates.folder(self.base) / candidates.ASSIGNMENT
        path.write_text(path.read_text() + "CAND-002\tx\tSRC-0001\t5\n")
        self.assertIn("SRC-0001: assigned 2 times", candidates.check(self.base))

    def test_missing_and_orphan_files_are_found(self):
        self.assign()
        self.worker_path("CAND-003").unlink()  # the third worker
        self.assertIn("CAND-003: assigned but its file is missing", candidates.check(self.base))
        (candidates.folder(self.base) / "CAND-009--stray.md").write_text(
            frontmatter.render({"id": "CAND-009", "type": "candidates"}, "x")
        )
        self.assertIn("CAND-009: has a file but no assignment", candidates.check(self.base))

    def test_citations_must_resolve_carry_a_hash_and_stay_inside_the_assignment(self):
        self.assign()
        outside = self.stamp("SRC-0003")
        cases = {
            "cites SRC-0003, which is not assigned": ("SRC-0003:L8#" + outside.split("#")[1]),
            "needs a citation": "",
            "SRC-0001:L99": "SRC-0001:L99",
            "text changed": "SRC-0001:L8#0000",
            "add #": "SRC-0001:L8",
        }
        for expected, citation in cases.items():
            self.fill("CAND-001", [("rule", "t", "claim", citation, "raw", "")])
            found = " | ".join(candidates.check(self.base))
            self.assertIn(expected, found, citation)

    def test_format_counts_and_caps_are_enforced(self):
        self.assign()
        good = self.stamp("SRC-0001")
        self.fill("CAND-001", [("rule", "t", " ".join(["w"] * 41), good, "raw", "")])
        self.assertIn("over 40 words", " ".join(candidates.check(self.base)))
        self.fill("CAND-001", [("mystery", "t", "c", good, "pending", "")])
        found = " ".join(candidates.check(self.base))
        self.assertIn("kind must be one of", found)
        self.assertIn("status must be one of", found)
        self.fill("CAND-001", [("rule", "t", "c", good, "merged", "")])
        self.assertIn("names the one it merged into", " ".join(candidates.check(self.base)))
        path = self.worker_path("CAND-001")
        self.fill("CAND-001", [("rule", "t", "c", good, "raw", "")])
        text = path.read_text().replace("count: 1", "count: 5")
        path.write_text(text)
        self.assertIn("count is 5 but the table has 1", " ".join(candidates.check(self.base)))
        path.write_text(text.replace("count: 5", "count: 1").replace("| 1 |", "| 2 |", 1))
        self.assertIn("item numbers must run 1..1", " ".join(candidates.check(self.base)))

    # ---- conflicts, status, show

    def test_same_topic_different_claim_is_a_conflict_with_both_citations(self):
        self.assign()
        a, b = self.stamp("SRC-0001"), self.stamp("SRC-0003")
        self.fill(
            "CAND-001", [("rule", "Refund window", "Refunds close after 14 days", a, "raw", "")]
        )
        self.fill(
            "CAND-002", [("rule", "refund-window", "Refunds close after 30 days", b, "raw", "")]
        )
        self.fill(
            "CAND-003", [("rule", "refund window", "refunds close after 14 days", a, "raw", "")]
        )
        pairs = candidates.conflicts(self.base)
        self.assertEqual(
            [(x.key, y.key) for x, y in pairs],
            [("CAND-001.1", "CAND-002.1"), ("CAND-002.1", "CAND-003.1")],
        )
        path, text = candidates.set_status(self.base, "CAND-002.1", "rejected")
        path.write_text(text)
        self.assertEqual(candidates.conflicts(self.base), [])

    def test_status_changes_are_validated_and_merge_needs_a_real_target(self):
        self.assign()
        cited = self.stamp("SRC-0001")
        self.fill(
            "CAND-001",
            [("rule", "t", "c", cited, "raw", ""), ("rule", "t", "c2", cited, "raw", "")],
        )
        path, text = candidates.set_status(self.base, "CAND-001.1", "merged", "CAND-001.2")
        path.write_text(text)
        self.assertEqual(candidates.item(self.base, "CAND-001.1").note, "CAND-001.2")
        self.assertEqual(candidates.check(self.base), [])
        for bad in (
            ("CAND-001.1", "merged", "CAND-001.1"),
            ("CAND-001.1", "merged", "CAND-009.1"),
            ("CAND-001.1", "bogus", ""),
            ("CAND-001.7", "accepted", ""),
            ("nope", "accepted", ""),
        ):
            with self.assertRaises(ValueError, msg=bad):
                candidates.set_status(self.base, *bad)

    def test_a_question_can_be_raised_from_a_candidate_by_key(self):
        self.assign()
        cited = self.stamp("SRC-0001")
        self.fill(
            "CAND-001", [("rule", "refund window", "Refunds close after 14 days", cited, "raw", "")]
        )
        ctx = recordops.Ctx(self.root, "REF", "sw-ingest", today=self.date)
        plan = recordops.question_new(
            ctx, "Which window applies", ["FEAT-001"], "PO", raised_from=["CAND-001.1"]
        )
        recordops.execute(ctx, plan, "q-new", "REF:Q-001")
        record = next((self.base / "records").glob("Q-001--*.md"))
        self.assertEqual(frontmatter.parse(record.read_text()).fm["raised_from"], [cited])
        with self.assertRaises(recordops.RecordError):
            recordops.question_new(ctx, "T", ["FEAT-001"], "PO", raised_from=["CAND-001.9"])

    # ---- command line

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_cli_assign_check_status_and_show(self):
        dry = self.cli("assign", "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertFalse(
            candidates.folder(self.base).exists()
            and any(candidates.folder(self.base).glob("CAND-*"))
        )
        self.assertEqual(self.cli("assign").returncode, 0)
        self.assertEqual(self.cli("check").stdout.strip(), "candidates clean")
        self.fill("CAND-001", [("rule", "t", "c", self.stamp("SRC-0001"), "raw", "")])
        shown = self.cli("show", "CAND-001.1")
        self.assertIn("Refunds close after 14 days.", shown.stdout)
        self.assertEqual(self.cli("status", "CAND-001.1", "accepted").returncode, 0)
        self.assertEqual(candidates.item(self.base, "CAND-001.1").status, "accepted")
        entries = writelog.read(self.base / "_meta/write-log.md")
        self.assertTrue(any("candidate-status" in e.fields for e in entries if e.kind == "INTENT"))
        self.snapshot("SRC-0009", "Late page")
        late = self.cli("check")
        self.assertEqual(late.returncode, 1)
        self.assertIn("SRC-0009: not assigned", late.stdout)
        self.assertEqual(self.cli("show", "CAND-009.1").returncode, 2)
