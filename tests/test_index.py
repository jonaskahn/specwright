"""The master index, crosswalk and read-first list are generated, deterministic and complete."""

from kitlib import frontmatter, graph, rtm
from tests.test_workflow import WorkflowTestCase

REGISTER = (
    "legacy_id\ttitle\tgroup\tsource_ref\n"
    "LEG-100\tRefund request\tG1\tpage-1\n"
    "LEG-200\tRefund approval\tG1\tpage-2\n"
    "LEG-300\tRefund payout\tG2\tpage-3\n"
)


class IndexTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        text = self.draft.read_text()
        self.draft.write_text(frontmatter.update(text, {"aliases": ["LEG-100", "refund-flow"]}))
        self.snapshot("SRC-0001", "page-1", "Refund policy page")
        self.snapshot("SRC-0002", "page-9", "Unrelated page")
        self.write(
            "records/Q-001.md",
            {
                "id": "Q-001",
                "type": "q",
                "title": "Which window applies?",
                "status": "open",
                "affects": ["REF:FEAT-001"],
            },
        )
        reg = self.base / "01-analysis/baseline/register.tsv"
        reg.parent.mkdir(parents=True)
        reg.write_text(REGISTER)
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md",
            "REF:FEAT-003",
            {"Kind": "story", "Title": "Payout", "Aliases": "LEG-300"},
            "sw-shape",
        )
        graph.build(self.root, "REF")

    def write(self, rel, fm, body="# Body\n"):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.render(fm, body))

    def snapshot(self, ident, remote, title):
        self.write(
            f"00-inbox/{ident}.md",
            {
                "id": ident,
                "type": "snapshot",
                "title": title,
                "status": "raw",
                "source": f"wiki:{remote}",
                "remote_id": remote,
                "remote_url": f"https://wiki.example.test/{remote}",
            },
            "Policy text.\n",
        )

    def table(self, name):
        lines = (self.base / "_meta" / name).read_text().splitlines()
        head = lines[1][2:].split("\t")
        return [dict(zip(head, ln.split("\t"), strict=False)) for ln in lines[2:]]

    def test_every_generated_file_is_written(self):
        for name in ("INDEX.md", "index.tsv", "CROSSWALK.tsv", "READ-FIRST.md"):
            self.assertTrue((self.base / "_meta" / name).is_file(), name)

    def test_rows_carry_name_aliases_status_and_links(self):
        rows = {r["key"]: r for r in self.table("index.tsv")}
        feat = rows["REF:FEAT-001"]
        self.assertEqual(feat["aliases"], "LEG-100|refund-flow")
        self.assertIn("blocked", feat["status"])
        self.assertIn("~affects:REF:Q-001", feat["links"])
        self.assertEqual(rows["REF:Q-001"]["name"], "Which window applies?")
        self.assertIn("affects:REF:FEAT-001", rows["REF:Q-001"]["links"])
        self.assertEqual(rows["REF:SRC-0001"]["origin"], "wiki:page-1")

    def test_a_reserved_feature_is_named_from_the_registry(self):
        row = {r["key"]: r for r in self.table("index.tsv")}["REF:FEAT-003"]
        self.assertEqual(row["name"], "Payout")
        self.assertEqual(row["aliases"], "LEG-300")
        self.assertNotIn("untitled", row["status"])

    def test_an_untitled_reservation_is_flagged_never_given_a_placeholder(self):
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md", "REF:FEAT-004", {"Kind": "story"}, "sw-spec"
        )
        graph.build(self.root, "REF")
        row = {r["key"]: r for r in self.table("index.tsv")}["REF:FEAT-004"]
        self.assertEqual(row["name"], "")
        self.assertIn("untitled", row["status"])

    def test_crosswalk_matches_and_lists_unmatched_on_both_sides(self):
        rows = {(r["legacy_id"], r["match"]): r for r in self.table("CROSSWALK.tsv")}
        matched = rows[("LEG-100", "matched")]
        self.assertEqual(matched["internal_key"], "REF:FEAT-001")
        self.assertEqual(matched["source_ids"], "REF:SRC-0001")
        self.assertEqual(matched["remote_id"], "page-1")
        self.assertEqual(matched["open_q"], "REF:Q-001")
        self.assertIn(("LEG-200", "no-feature"), rows)
        self.assertIn(("LEG-300", "no-source"), rows)
        self.assertEqual(rows[("", "no-register")]["source_ids"], "REF:SRC-0002")

    def test_read_first_names_the_fixed_reading_order(self):
        text = (self.base / "_meta/READ-FIRST.md").read_text()
        order = ["project.yaml", "AGENTS.md", "INDEX.md", "CROSSWALK.tsv", "graph.py board"]
        positions = [text.index(item) for item in order]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("do not open folders", text)

    def test_a_second_build_changes_nothing(self):
        before = {p: p.read_bytes() for p in (self.base / "_meta").glob("*") if p.is_file()}
        self.assertEqual(graph.build(self.root, "REF"), [])
        after = {p: p.read_bytes() for p in (self.base / "_meta").glob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_hand_edits_to_generated_files_are_reported(self):
        marker = "was edited by hand"
        self.assertFalse([f for f in graph.check(self.root, "REF") if marker in f])
        path = self.base / "_meta/INDEX.md"
        path.write_text(path.read_text() + "| hand | edit |\n")
        self.assertIn(
            "REF: _meta/INDEX.md was edited by hand; run build", graph.check(self.root, "REF")
        )
        graph.build(self.root, "REF")
        self.assertFalse([f for f in graph.check(self.root, "REF") if marker in f])
