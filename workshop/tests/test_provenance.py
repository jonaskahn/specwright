"""An attributed amendment corrects provenance; the snapshot and its bytes never change."""

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from kitlib import graph, graph_query, ids, provenance, writelog
from tests.test_workflow import WorkflowTestCase

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sw-ingest/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("ingest_for_provenance", SCRIPTS / "to_md.py")
to_md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(to_md)
NOW = datetime(2026, 11, 12, 9, 0, 0, tzinfo=timezone.utc)


class ProvenanceTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        source = self.root / "policy.txt"
        source.write_text("# Refund policy\n\nRefunds close after 14 days of delivery.\n")
        to_md.ingest(source, self.base / "00-inbox", scope="REF", source="file:///policy.txt")
        self.snapshot = ids.find_record(self.base / "00-inbox", "SRC-0001")

    def amend(self, **fields):
        values = {"source": "wiki:page-77", "remote_url": "https://wiki.example.test/page-77"}
        values.update(fields)
        path, line = provenance.plan(
            self.base, "SRC-0001", values, "BA | An Tran", "export lost the page link", now=NOW
        )
        provenance.append(path, line)
        return path

    def test_an_amendment_is_recorded_and_the_snapshot_is_untouched(self):
        before = self.snapshot.read_bytes()
        path = self.amend()
        self.assertEqual(self.snapshot.read_bytes(), before)
        (entry,) = provenance.history(self.base, "SRC-0001")
        self.assertEqual(entry["by"], "BA | An Tran")
        self.assertEqual(entry["previous"]["source"], "file:///policy.txt")
        self.assertEqual(entry["amended_at"], "2026-11-12T09:00:00Z")
        self.assertEqual(path.name, "SRC-0001.jsonl")

    def test_effective_provenance_applies_amendments_in_order_and_grows_aliases(self):
        self.amend()
        self.amend(source_version="v7", source="wiki:page-78", remote_id="page-78")
        header = {"source": "old", "aliases": ["POL-1"]}
        merged = provenance.effective(self.base, "SRC-0001", header)
        self.assertEqual((merged["source"], merged["source_version"]), ("wiki:page-78", "v7"))
        self.assertEqual(
            merged["aliases"],
            ["POL-1", "https://wiki.example.test/page-77", "page-78"],
        )

    def test_the_index_shows_the_amended_origin_and_finds_the_new_names(self):
        self.amend(remote_id="page-77")
        graph.build(self.root, "REF")
        store = graph_query.Store(self.root, "REF")
        self.assertEqual(store.freshness(), "fresh")
        self.assertEqual(store.resolve("page-77"), "REF:SRC-0001")
        row = next(
            line
            for line in (self.base / "_meta/index.tsv").read_text().splitlines()
            if line.startswith("REF:SRC-0001")
        )
        self.assertIn("\twiki:page-77\t", row)

    def test_an_amendment_makes_a_built_graph_stale(self):
        graph.build(self.root, "REF")
        self.amend()
        self.assertEqual(graph_query.Store(self.root, "REF").freshness(), "stale")

    def test_invalid_amendments_are_refused(self):
        def plan(**kw):
            args = {"fields": {"source": "x"}, "by": "BA | An", "reason": "fix", **kw}
            return provenance.plan(self.base, "SRC-0001", **args)

        for bad in (
            {"fields": {}},
            {"fields": {"title": "renamed"}},
            {"by": " "},
            {"reason": ""},
            {"fields": {"source": "file:///policy.txt"}},  # already says this
        ):
            with self.assertRaises(provenance.ProvenanceError, msg=bad):
                plan(**bad)
        with self.assertRaises(provenance.ProvenanceError):
            provenance.plan(self.base, "SRC-0042", {"source": "x"}, "BA | An", "fix")
        with self.assertRaises(provenance.ProvenanceError):
            provenance.plan(self.base, "FEAT-001", {"source": "x"}, "BA | An", "fix")

    def test_changed_original_bytes_block_an_amendment(self):
        raw = next((self.base / "00-inbox/raw").iterdir())
        raw.write_bytes(b"tampered")
        with self.assertRaisesRegex(provenance.ProvenanceError, "original bytes"):
            provenance.plan(self.base, "SRC-0001", {"source": "x"}, "BA | An", "fix")

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "provenance.py"), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_cli_dry_run_amend_and_show(self):
        base = [
            "amend",
            "SRC-0001",
            "--source",
            "wiki:page-5",
            "--by",
            "BA | An",
            "--reason",
            "fix",
        ]
        dry = self.cli(*base, "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(provenance.history(self.base, "SRC-0001"), [])
        done = self.cli(*base)
        self.assertEqual(done.returncode, 0, done.stderr)
        shown = json.loads(done.stdout)
        self.assertEqual(shown["effective"]["source"], "wiki:page-5")
        self.assertEqual(len(shown["amendments"]), 1)
        log = writelog.read(self.base / "_meta/write-log.md")
        self.assertTrue(any("provenance-amend" in e.fields for e in log if e.kind == "INTENT"))
        again = self.cli(*base)
        self.assertEqual(again.returncode, 2)
        self.assertEqual(self.cli("show", "SRC-0001").returncode, 0)
