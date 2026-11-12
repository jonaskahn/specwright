"""Plan and publish reports show a feature's name and aliases next to its ID."""

import subprocess
import sys
from pathlib import Path

from kitlib import frontmatter, jira_diff, publish, rtm, task_validation
from tests import test_workflow
from tests.test_workflow import WorkflowTestCase

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "skills/sw-plan/scripts/check_tasks.py"
PUBLISH = ROOT / "skills/sw-publish/scripts/publish.py"


class ReportNameTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        text = self.draft.read_text()
        fields = {"title": "Request a refund", "aliases": ["LEG-100"], "status": "ready-to-publish"}
        self.draft.write_text(frontmatter.update(text, fields))
        rtm.registry_upsert(
            self.base / "_meta/id-registry.md",
            "REF:FEAT-001",
            {"Kind": "story", "Aliases": "LEG-100|refund-flow"},
            "sw-shape",
        )

    def test_label_joins_id_name_and_aliases(self):
        self.assertEqual(
            task_validation.label(self.base, "FEAT-001"), "FEAT-001 — Request a refund (LEG-100)"
        )
        self.assertEqual(task_validation.label(self.base, "FEAT-404"), "FEAT-404")

    def test_publish_names_merge_front_matter_and_registry_aliases_once(self):
        ctx = publish.context(self.root, "FEAT-001", "REF")
        name, aliases = publish.names(ctx, self.draft.read_text())
        self.assertEqual((name, aliases), ("Request a refund", ["LEG-100", "refund-flow"]))

    def test_the_rendered_plan_shows_names_but_the_hash_does_not_depend_on_them(self):
        draft = self.draft.read_text()
        result = jira_diff.plan("", "", draft, scope_id="REF:FEAT-001")
        bare = jira_diff.render_plan(result)
        self.assertNotIn("Name:", bare)
        hash_before = result["short_hash"]
        result["name"], result["aliases"] = "Request a refund", ["LEG-100"]
        named = jira_diff.render_plan(result)
        self.assertIn("Name: Request a refund", named)
        self.assertIn("Aliases: LEG-100", named)
        self.assertEqual(result["short_hash"], hash_before)

    def test_the_task_check_prints_the_label_first(self):
        result = subprocess.run(
            [sys.executable, str(PLAN), "--cwd", str(self.root), "--feat", "FEAT-001"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        first = result.stdout.splitlines()[0]
        self.assertEqual(first, "FEAT-001 — Request a refund (LEG-100)")

    def test_the_publish_plan_command_shows_the_name(self):
        test_workflow.PublishTests.promote(
            self
        )  # approval, plan and tasks, as the publish tests set them up
        result = subprocess.run(
            [sys.executable, str(PUBLISH), "plan", "--root", str(self.root), "--feat", "FEAT-001"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Name: Request a refund", result.stdout)
        self.assertIn("Aliases: LEG-100, refund-flow", result.stdout)
