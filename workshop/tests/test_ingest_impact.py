"""Imported evidence proposes changes; it never silently rewrites a contract."""

from kitlib import frontmatter, graph, graph_query, ingest_impact
from tests.test_workflow import WorkflowTestCase


class ImpactTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        self.source = self.base / "00-inbox/SRC-0001.md"
        self.source.write_text(
            frontmatter.render(
                {"id": "SRC-0001", "type": "snapshot", "scope": "REF", "status": "raw"},
                "The refund window should be 30 days, not 14 days.\n",
            )
        )

    def test_one_match_remains_a_suggestion(self):
        graph.build(self.root, "REF")
        results = ingest_impact.candidates(
            graph_query.Store(self.root, "REF"), "refund delivered order"
        )
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["confirmed"])

    def test_impact_proposal_is_idempotent_and_preserves_artifacts(self):
        before = self.draft.read_bytes()
        source = self.source.read_bytes()
        args = (self.base, "SRC-0001", "REF:FEAT-001", "30 days", "14-day refund window")
        path = ingest_impact.propose(*args)
        self.assertEqual(ingest_impact.propose(*args), path)
        self.assertEqual(self.draft.read_bytes(), before)
        self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual(frontmatter.parse(path.read_text()).fm["status"], "proposed")
        self.assertFalse((self.base / "_meta/history").exists())

    def test_quotes_must_exist_in_both_inputs(self):
        with self.assertRaises(ValueError):
            ingest_impact.propose(self.base, "SRC-0001", "FEAT-001", "invented", "14-day")

    def test_backup_is_exact_idempotent_and_excluded_from_scan(self):
        before = self.draft.read_bytes()
        path = ingest_impact.backup(self.base, "02-drafts/FEAT-001.story.md")
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(ingest_impact.backup(self.base, "02-drafts/FEAT-001.story.md"), path)
        from kitlib import rtm

        _, findings = rtm.scan(self.root)
        self.assertFalse(any("duplicate" in f for f in findings))
