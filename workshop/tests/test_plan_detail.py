"""The detailed plan lists its tasks and gives each a definition of done, criteria and coverage."""

from kitlib import frontmatter, task_validation
from tests.test_task_progress import TaskProgressTests

SECTIONS = "".join(f"## {n}\n\nx\n\n" for n in task_validation.PLAN_SECTIONS)


def task_section(tid, skip=None):
    lines = {
        "Files": "src/a.py (new)",
        "Change": "adds a",
        "Test": "tests/test_a.py::test_a",
        "DoD": "a refund is stored",
        "Accepts": "AC-001-1",
        "Coverage": "line 80%",
    }
    body = "".join(f"{k}: {v}\n" for k, v in lines.items() if k != skip)
    return f"### {tid} — [backend] Do it\n{body}\n"


class PlanDetailTests(TaskProgressTests):
    def plan(self, tasks=("TASK-001-1", "TASK-001-2"), listed=None, skip=None):
        self.tasks()
        text = SECTIONS + "## Tasks\n\n" + "".join(task_section(t, skip) for t in tasks)
        fm = {"feat": "FEAT-001", "type": "plan", "tasks": list(listed or tasks)}
        (self.base / "03-plan" / "FEAT-001.plan.md").write_text(frontmatter.render(fm, text))
        return task_validation.plan_findings(self.base, "FEAT-001")

    def test_a_complete_plan_has_no_findings(self):
        self.assertEqual(self.plan(), [])

    def test_a_task_needs_dod_accepts_and_coverage(self):
        for field in ("DoD", "Accepts", "Coverage"):
            self.assertIn(
                f"TASK-001-1: plan section has no {field}: line",
                self.plan(skip=field),
            )

    def test_the_front_matter_must_list_every_active_task(self):
        found = self.plan(listed=["TASK-001-1"])
        self.assertTrue(any("must list every active task" in f for f in found), found)
