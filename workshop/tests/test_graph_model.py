"""Epic membership and open-question counts come only from declared, kind-correct edges."""

from kitlib import frontmatter, graph, graph_query, rtm
from tests.test_workflow import WorkflowTestCase


class GraphModelTests(WorkflowTestCase):
    def write(self, rel, fm, body="# Title\n"):
        path = self.base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(frontmatter.render(fm, body))

    def epic_and_split(self, **split):
        self.write(
            "01-analysis/epics/EPIC-001.md",
            {"id": "EPIC-001", "type": "epic", "scope": "REF", "status": "approved"},
            "# Refunds\n",
        )
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md", "REF:FEAT-002", {"Kind": "story"}, "sw-spec"
        )
        fm = {
            "id": "DEC-001",
            "type": "dec",
            "status": "accepted",
            "subtype": "accepted-split",
            "scope": "REF",
            "features": ["REF:FEAT-001", "REF:FEAT-002"],
            "evidence_url": "https://example.test/split/1",
        }
        fm.update(split)
        self.write("records/DEC-001.md", fm, "# Accepted split\n")

    def members(self, epic="REF:EPIC-001"):
        store = graph_query.Store(self.root, "REF")
        return sorted(e.src for e in store.edges_for({epic}, "in") if e.rel == "member_of")

    def test_decision_is_not_an_epic_member(self):
        self.epic_and_split(epic="REF:EPIC-001")
        graph.build(self.root, "REF")
        self.assertEqual(self.members(), ["REF:FEAT-001", "REF:FEAT-002"])
        page = (self.base / "_meta/graph/maps/REF_EPIC-001.md").read_text()
        self.assertNotIn("DEC-001", page)

    def test_one_decision_can_place_features_in_several_epics(self):
        self.epic_and_split(epics=["REF:EPIC-001", "REF:EPIC-002"])
        self.write(
            "01-analysis/epics/EPIC-002.md",
            {"id": "EPIC-002", "type": "epic", "scope": "REF", "status": "approved"},
            "# Payments\n",
        )
        graph.build(self.root, "REF")
        self.assertEqual(self.members("REF:EPIC-001"), ["REF:FEAT-001", "REF:FEAT-002"])
        self.assertEqual(self.members("REF:EPIC-002"), ["REF:FEAT-001", "REF:FEAT-002"])

    def question(self, qid, **extra):
        fm = {"id": qid, "type": "q", "scope": "REF", "status": "open", "affects": ["REF:FEAT-001"]}
        fm.update(extra)
        self.write(f"records/{qid}.md", fm, f"# {qid} question\n")

    def lifecycle(self):
        graph.build(self.root, "REF")
        rows = graph_query.board(graph_query.Store(self.root, "REF"))
        return next(r for r in rows if r["id"] == "REF:FEAT-001")

    def test_open_question_blocks_the_board_row(self):
        self.question("Q-001")
        self.question("Q-002", blocking=False)
        row = self.lifecycle()
        self.assertEqual(row["open_q"], ["REF:Q-001", "REF:Q-002"])
        self.assertEqual(row["blocked_by_q"], ["REF:Q-001"])

    def test_proposed_counts_and_answered_does_not(self):
        self.question("Q-001", status="proposed")
        self.question("Q-002", status="answered")
        self.assertEqual(self.lifecycle()["open_q"], ["REF:Q-001"])

    def test_mention_only_question_is_not_counted(self):
        self.question("Q-001", affects=[])
        self.write(
            "records/Q-001.md",
            {"id": "Q-001", "type": "q", "scope": "REF", "status": "open"},
            "# Mentions FEAT-001 only\n",
        )
        self.assertEqual(self.lifecycle()["open_q"], [])

    def test_a_stray_folder_is_reported_by_build_check_and_the_work_folder_is_ignored(self):
        (self.base / "scratch").mkdir()
        (self.base / "_meta/work").mkdir(parents=True, exist_ok=True)
        (self.base / "_meta/work/notes.md").write_text("---\nid: FEAT-009\n---\nnot evidence\n")
        graph.build(self.root, "REF")
        self.assertIn(
            "REF: stray folder scratch/ is not read as evidence",
            graph.drift_warnings(self.root, "REF"),
        )
        self.assertIn(
            "REF: stray folder scratch/ is not read as evidence", graph.check(self.root, "REF")
        )
        store = graph_query.Store(self.root, "REF")
        self.assertIsNone(store.node("REF:FEAT-009"))
        self.assertEqual(store.freshness(), "fresh")
        (self.base / "_meta/work/more.md").write_text("changed working file")
        self.assertEqual(store.freshness(), "fresh")
