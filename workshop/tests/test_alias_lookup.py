"""Any name an item goes by finds its record; an ambiguous name asks and never picks."""

import subprocess
import sys
from pathlib import Path

from kitlib import frontmatter, graph, graph_query
from tests.test_workflow import WorkflowTestCase

GRAPH = Path(__file__).resolve().parents[2] / "skills/_shared/scripts/graph.py"


class AliasLookupTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        text = self.draft.read_text()
        fields = {"aliases": ["LEG-100", "Refund Flow"], "title": "Refund request"}
        self.draft.write_text(frontmatter.update(text, fields))
        self.add(
            "00-inbox/SRC-0001.md",
            {
                "id": "SRC-0001",
                "type": "snapshot",
                "status": "raw",
                "title": "Refund policy page",
                "aliases": ["page-1", "https://wiki.example.test/page-1", "WIKI-7"],
                "remote_id": "page-1",
            },
        )
        self.add(
            "records/Q-001.md",
            {"id": "Q-001", "type": "q", "title": "Refund window", "status": "open"},
        )
        graph.build(self.root, "REF")
        self.store = graph_query.Store(self.root, "REF")

    def add(self, rel, fm):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.render(fm, "# Body\n"))

    def test_each_kind_of_name_resolves_to_one_record(self):
        for name, key in (
            ("REF:FEAT-001", "REF:FEAT-001"),
            ("FEAT-001", "REF:FEAT-001"),
            ("LEG-100", "REF:FEAT-001"),
            ("leg-100", "REF:FEAT-001"),
            ("refund flow", "REF:FEAT-001"),
            ("page-1", "REF:SRC-0001"),
            ("https://wiki.example.test/page-1", "REF:SRC-0001"),
            ("WIKI-7", "REF:SRC-0001"),
        ):
            self.assertEqual(self.store.resolve(name), key, name)

    def test_title_fragments_resolve_only_for_show(self):
        self.assertEqual(self.store.resolve("refund request", fuzzy=True), "REF:FEAT-001")
        with self.assertRaises(graph_query.QueryError) as caught:
            self.store.resolve("refund request")
        self.assertEqual(caught.exception.code, 3)

    def test_an_ambiguous_name_lists_candidates_and_never_picks(self):
        with self.assertRaises(graph_query.QueryError) as caught:
            self.store.resolve("refund", fuzzy=True)
        self.assertEqual(caught.exception.code, 3)
        self.assertGreaterEqual(len(caught.exception.options), 3)

    def test_unknown_name_asks(self):
        with self.assertRaises(graph_query.QueryError) as caught:
            self.store.resolve("no such thing")
        self.assertEqual(caught.exception.code, 3)

    def test_story_word_still_maps_to_feat(self):
        self.assertEqual(self.store.resolve("STORY-001"), "REF:FEAT-001")

    def test_find_searches_aliases_and_shows_them(self):
        lines = graph_query.find(self.store, "leg-100", None, None, None, None, 0, 20)
        self.assertEqual(len(lines), 1)
        self.assertIn("aka: LEG-100|Refund Flow", lines[0])

    def test_show_prints_aliases_links_and_the_crosswalk_row(self):
        lines = graph_query.show(self.store, "REF:FEAT-001")
        self.assertIn("aliases: LEG-100, Refund Flow", lines)
        self.assertTrue(
            any(line.startswith("crosswalk: LEG-100 -> REF:FEAT-001") for line in lines), lines
        )

    def run_graph(self, *args):
        return subprocess.run(
            [sys.executable, str(GRAPH), *args, "--cwd", str(self.root), "--scope", "REF"],
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_cli_resolves_a_legacy_id_and_asks_on_ambiguity(self):
        shown = self.run_graph("show", "LEG-100")
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("REF:FEAT-001 [feat]", shown.stdout)
        ambiguous = self.run_graph("show", "refund")
        self.assertEqual(ambiguous.returncode, 3)
        self.assertIn("candidate: REF:FEAT-001", ambiguous.stderr)
