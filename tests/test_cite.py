"""Durable citations are checked, copied and rebased by program and never rewritten."""

import json
import subprocess
import sys
from pathlib import Path

from kitlib import cite, frontmatter
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parent.parent / "skills/_shared/scripts/cite.py"
SNAPSHOT = (
    "---\nid: SRC-0001\ntype: snapshot\nstatus: raw\ntitle: Policy\naliases: []\n---\n"
    "Refunds close after 14 days.\n\nPayout needs approval.\nSecond line of the rule.\n"
)


class CiteTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        (self.base / "00-inbox/SRC-0001.md").write_text(SNAPSHOT)
        self.sources = cite.Sources(self.base)

    def note(self, text, name="records/Q-001.md"):
        path = self.base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.render({"id": "Q-001", "type": "q", "status": "open"}, text))
        return path

    def codes(self, text):
        return [p.code for p in cite.problems(self.sources, text)]

    def test_parse_forms(self):
        found = cite.find("see SRC-0001:L7, REF:SRC-0002:L3-L5#a1b2 and SRC-0001:L4-6")
        self.assertEqual(
            [(c.scope, c.source, c.start, c.end, c.digest) for c in found],
            [
                (None, "SRC-0001", 7, 7, ""),
                ("REF", "SRC-0002", 3, 5, "a1b2"),
                (None, "SRC-0001", 4, 6, ""),
            ],
        )
        self.assertEqual(found[1].text(), "SRC-0002:L3-L5#a1b2")

    def test_a_correct_citation_is_clean_and_stamping_adds_the_hash(self):
        stamped = cite.stamp(self.sources, cite.parse_one("SRC-0001:L8"))
        self.assertRegex(stamped, r"^SRC-0001:L8#[0-9a-f]{4}$")
        self.assertEqual(self.codes(f"x {stamped} y"), [])

    def test_quote_copies_the_exact_lines(self):
        text = cite.quote(self.sources, cite.parse_one("SRC-0001:L10-L11"))
        self.assertEqual(text, "Payout needs approval.\nSecond line of the rule.")

    def test_dangling_citations_are_named(self):
        self.assertEqual(self.codes("SRC-0001:L99"), ["line-out-of-range"])
        self.assertEqual(self.codes("SRC-0001:L9"), ["blank-line"])
        self.assertEqual(self.codes("SRC-0001:L8#0000"), ["hash-mismatch"])
        self.assertEqual(self.codes("SRC-0044:L1"), ["missing-source"])
        self.assertEqual(self.codes("SRC-0001:L5-L2"), ["line-out-of-range"])

    def test_missing_hash_only_matters_when_required(self):
        self.assertEqual(self.codes("SRC-0001:L8"), [])
        found = cite.problems(self.sources, "SRC-0001:L8", require_hash=True)
        self.assertEqual([p.code for p in found], ["no-hash"])

    def test_superseded_and_index_only_sources_are_weak_evidence(self):
        newer = SNAPSHOT.replace("SRC-0001", "SRC-0002").replace(
            "status: raw", "status: raw\nsupersedes: [SRC-0001]"
        )
        (self.base / "00-inbox/SRC-0002.md").write_text(newer)
        stale = cite.problems(cite.Sources(self.base), "SRC-0001:L8")
        self.assertEqual([(p.code, p.severity) for p in stale], [("superseded-source", "warn")])
        index_only = SNAPSHOT.replace("status: raw", "status: raw\ncontent_class: index-only")
        (self.base / "00-inbox/SRC-0003.md").write_text(index_only.replace("SRC-0001", "SRC-0003"))
        weak = cite.problems(cite.Sources(self.base), "SRC-0003:L8")
        self.assertEqual([(p.code, p.severity) for p in weak], [("weak-source", "warn")])

    def test_verify_walks_a_folder_and_skips_snapshots(self):
        self.note("Window: SRC-0001:L99\n")
        found = cite.verify(self.base, self.base)
        self.assertEqual(
            [(f, p.code) for f, p in found], [("records/Q-001.md", "line-out-of-range")]
        )

    def test_rebase_proposes_new_lines_and_flags_what_it_cannot_move(self):
        moved = (
            SNAPSHOT.replace("Refunds close", "Intro line.\nRefunds close")
            .replace("SRC-0001", "SRC-0002")
            .replace("Payout needs approval.", "Payout needs sign-off.")
        )
        (self.base / "00-inbox/SRC-0002.md").write_text(moved)
        citing = [("a.md", c) for c in cite.find("SRC-0001:L8 and SRC-0001:L10")]
        rows = cite.rebase(self.sources, cite.Sources(self.base), "SRC-0001", "SRC-0002", citing)
        self.assertRegex(rows[0][3], r"^SRC-0002:L9#[0-9a-f]{4}$")
        self.assertEqual(rows[1][3], "")
        self.assertEqual(rows[1][4], "text not found in the new source")

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_cli_exit_codes_and_output(self):
        self.note("ok SRC-0001:L8\n")
        clean = self.run_cli("verify")
        self.assertEqual((clean.returncode, clean.stdout.strip()), (0, "citations clean"))
        self.note("bad SRC-0001:L99\n")
        broken = self.run_cli("verify", "--format", "json")
        self.assertEqual(broken.returncode, 1)
        self.assertEqual(json.loads(broken.stdout)["findings"][0]["code"], "line-out-of-range")
        self.assertEqual(
            self.run_cli("quote", "SRC-0001:L8").stdout.strip(), "Refunds close after 14 days."
        )
        self.assertEqual(self.run_cli("quote", "SRC-0001:L99").returncode, 2)

    def test_the_old_snapshot_is_left_untouched_by_a_rebase(self):
        before = (self.base / "00-inbox/SRC-0001.md").read_bytes()
        note = self.note("cites SRC-0001:L8\n")
        note_before = note.read_bytes()
        (self.base / "00-inbox/SRC-0002.md").write_text(SNAPSHOT.replace("SRC-0001", "SRC-0002"))
        result = self.run_cli("rebase", "SRC-0001", "SRC-0002")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.base / "00-inbox/SRC-0001.md").read_bytes(), before)
        self.assertEqual(note.read_bytes(), note_before)
