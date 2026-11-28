import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, graph, graph_query, readiness, workspace

ROOT = Path(__file__).resolve().parents[2]
GRAPH_CLI = ROOT / "skills/_shared/scripts/graph.py"
FINISH_CLI = ROOT / "skills/_shared/scripts/finish.py"


def story(ident, title, **extra):
    fm = {"id": ident, "type": "feature", "scope": "REF", "title": title, "status": "draft"}
    fm.update(extra)
    return frontmatter.render(fm, "## Goal\n\nA goal.\n")


def tasks(feat, *rows):
    body = ""
    for tid, status, depends in rows:
        body += (
            f"### {tid} — [backend] Do {tid}\nTraces to: AC-001-1\nStatus: {status}\n"
            f"Depends on: {depends}\nDone when: it works\n\n"
        )
    return frontmatter.render({"feat": feat, "status": "ready"}, body)


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve() / ".specwright"
        workspace.init(self.root, "flat", "REF", "Refunds")
        epic = frontmatter.render(
            {
                "id": "EPIC-001",
                "type": "epic",
                "scope": "REF",
                "title": "Refunds",
                "status": "draft",
            },
            "## Outcome\n\nRefunds.\n",
        )
        epic_file = self.root / "epics/EPIC-001/EPIC-001--refunds.md"
        epic_file.parent.mkdir(parents=True, exist_ok=True)
        epic_file.write_text(epic)
        self.put("FEAT-001", story("FEAT-001", "First", epic="EPIC-001"))
        self.put("FEAT-002", story("FEAT-002", "Second", epic="EPIC-001", depends_on=["FEAT-001"]))

    def put(self, feat, text):
        path = self.root / "features" / feat / f"{feat}.story.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def put_tasks(self, feat, text):
        path = self.root / "tasks" / feat / f"{feat}.tasks.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def state(self, plan1=None, plan2=None):
        for name, text in (("FEAT-001", plan1), ("FEAT-002", plan2)):
            if text:
                self.put_tasks(name, text)
        return readiness.compute(graph.build_graph(self.root, ["REF"]))

    def test_a_feature_waits_for_the_feature_it_depends_on(self):
        out = self.state()
        self.assertTrue(out["REF:FEAT-001"]["ready"])
        self.assertEqual(out["REF:FEAT-002"]["blocked_by"], ["REF:FEAT-001"])
        self.assertFalse(out["REF:FEAT-002"]["ready"])

    def test_status_rolls_up_from_tasks_to_feature_and_epic(self):
        out = self.state(
            tasks("FEAT-001", ("TASK-001-1", "done", "None"), ("TASK-001-2", "todo", "None"))
        )
        self.assertEqual(out["REF:FEAT-001"]["status"], "in_progress")
        self.assertEqual(out["REF:EPIC-001"]["status"], "in_progress")
        out = self.state(
            tasks("FEAT-001", ("TASK-001-1", "done", "None"), ("TASK-001-2", "done", "None"))
        )
        self.assertEqual(out["REF:FEAT-001"]["status"], "done")
        self.assertEqual(out["REF:FEAT-002"]["blocked_by"], [])
        self.assertTrue(out["REF:FEAT-002"]["ready"])

    def test_a_task_waits_for_the_task_it_depends_on(self):
        out = self.state(
            tasks("FEAT-001", ("TASK-001-1", "todo", "None"), ("TASK-001-2", "todo", "TASK-001-1"))
        )
        self.assertTrue(out["REF:TASK-001-1"]["ready"])
        self.assertEqual(out["REF:TASK-001-2"]["blocked_by"], ["REF:TASK-001-1"])

    def test_finishing_a_task_names_what_it_opened(self):
        before = self.state(
            tasks("FEAT-001", ("TASK-001-1", "todo", "None"), ("TASK-001-2", "todo", "TASK-001-1"))
        )
        after = self.state(
            tasks("FEAT-001", ("TASK-001-1", "done", "None"), ("TASK-001-2", "todo", "TASK-001-1"))
        )
        self.assertEqual(readiness.newly_ready(before, after), ["REF:TASK-001-2"])

    def test_the_ready_file_and_command_list_the_same_items(self):
        graph.build(self.root, "REF")
        rows = graph_query.ready(graph_query.Store(self.root, "REF"))
        self.assertEqual(
            {r["key"] for r in rows if r["ready"] == "yes"}, {"REF:EPIC-001", "REF:FEAT-001"}
        )
        done = subprocess.run(
            [
                sys.executable,
                str(GRAPH_CLI),
                "ready",
                "--cwd",
                str(self.root),
                "--kind",
                "feat",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual([i["key"] for i in json.loads(done.stdout)["items"]], ["REF:FEAT-001"])

    def test_finishing_a_station_reports_what_it_opened(self):
        self.put_tasks(
            "FEAT-001",
            tasks("FEAT-001", ("TASK-001-1", "todo", "None"), ("TASK-001-2", "todo", "TASK-001-1")),
        )
        graph.build(self.root, "REF")
        self.put_tasks(
            "FEAT-001",
            tasks("FEAT-001", ("TASK-001-1", "done", "None"), ("TASK-001-2", "todo", "TASK-001-1")),
        )
        done = subprocess.run(
            [
                sys.executable,
                str(FINISH_CLI),
                "--skill",
                "sw-forge",
                "--subject",
                "done",
                "--cwd",
                str(self.root),
                "--no-checkpoint",
            ],
            capture_output=True,
            text=True,
        )
        report = json.loads(done.stdout)
        self.assertIn("REF:TASK-001-2", report["newly_ready"])

    def test_a_dependency_cycle_is_a_finding(self):
        self.put("FEAT-001", story("FEAT-001", "First", epic="EPIC-001", depends_on=["FEAT-002"]))
        graph.build(self.root, "REF")
        findings = graph.check(self.root, "REF")
        self.assertIn("REF:FEAT-001: depends_on forms a cycle", findings)
        self.assertIn("REF:FEAT-002: depends_on forms a cycle", findings)


if __name__ == "__main__":
    unittest.main()
