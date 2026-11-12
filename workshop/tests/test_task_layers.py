"""Layer prefixes and visual references on tasks are checked, not just described."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kitlib import frontmatter, hashing, markdown, schema, tables, task_validation

ROOT = Path(__file__).resolve().parents[2]
GOOD = (ROOT / "workshop/fixtures/lint/good-story.md").read_text()


def task(n, title, traces, extra=""):
    return f"### TASK-001-{n} — {title}\nTraces to: {traces}\nDone when: observable{extra}\n"


class LayerTests(unittest.TestCase):
    def test_layer_prefix_parsing(self):
        self.assertEqual(markdown.task_layer("[Backend] Record it"), "backend")
        self.assertEqual(markdown.task_layer("[frontend] Show it [P]"), "frontend")
        self.assertIsNone(markdown.task_layer("Record it"))
        self.assertIsNone(markdown.task_layer("[backend]"))
        self.assertIsNone(markdown.task_layer("Record it [backend]"))

    def test_visuals_is_a_task_field(self):
        body = task(1, "[frontend] Show it", "AC-001-1", "\nVisuals: ASSET-001, diagrams/flow.svg")
        block = markdown.task_blocks(body)["TASK-001-1"]
        self.assertEqual(block.field_line("Visuals"), "ASSET-001, diagrams/flow.svg")


class CheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        for name in ("02-drafts", "03-plan", "_meta", "diagrams"):
            (self.base / name).mkdir()
        patcher = mock.patch("kitlib.lifecycle.approval_state", return_value="fresh")
        patcher.start()
        self.addCleanup(patcher.stop)

    def registry(self, kind="mockup"):
        table = tables.Table(list(schema.ASSET_REGISTRY_COLUMNS))
        table.rows = [
            ["ASSET-001", "assets/ASSET-001.png", kind, "sha", "now", "user", "", "captured"]
        ]
        (self.base / "_meta/asset-registry.md").write_text("# registry\n\n" + table.render())

    def write(self, tasks, assets=()):
        story = frontmatter.update(GOOD, {"assets": list(assets)})
        (self.base / "02-drafts/FEAT-001.story.md").write_text(story)
        fm = {"feat": "FEAT-001", "status": "draft", "spec_hash": hashing.draft_hash(story)}
        (self.base / "03-plan/FEAT-001.tasks.md").write_text(frontmatter.render(fm, tasks))

    def findings(self):
        return task_validation.check(self.base, "FEAT-001")[1]

    def test_clean_split_passes(self):
        self.registry()
        self.write(
            task(1, "[backend] Record the request", "AC-001-1")
            + task(2, "[frontend] Show the request form", "AC-001-2", "\nVisuals: ASSET-001"),
            assets=["ASSET-001"],
        )
        self.assertEqual(self.findings(), [])

    def test_missing_and_unknown_layer(self):
        self.write(task(1, "Record", "AC-001-1") + task(2, "[cloud] Deploy", "AC-001-2"))
        found = "\n".join(self.findings())
        self.assertIn("TASK-001-1: title needs a layer prefix", found)
        self.assertIn("TASK-001-2: unknown layer [cloud]", found)

    def test_ui_task_must_cite_a_visual_when_the_story_has_one(self):
        self.registry()
        tasks = task(1, "[frontend] Show it", "AC-001-1") + task(
            2, "[backend] Store it", "AC-001-2"
        )
        self.write(tasks, assets=["ASSET-001"])
        found = self.findings()
        self.assertEqual(len(found), 1)
        self.assertIn("TASK-001-1: a frontend task needs Visuals", found[0])
        self.write(tasks)  # the story lists no visual: nothing to cite
        self.assertEqual(self.findings(), [])

    def test_a_document_asset_is_not_a_visual(self):
        self.registry("document")
        self.write(
            task(1, "[frontend] Show it", "AC-001-1") + task(2, "[backend] Store it", "AC-001-2"),
            assets=["ASSET-001"],
        )
        self.assertEqual(self.findings(), [])

    def test_visuals_must_exist(self):
        self.registry()
        self.write(
            task(1, "[backend] Store it", "AC-001-1", "\nVisuals: ASSET-009")
            + task(2, "[design] Draw it", "AC-001-2", "\nVisuals: diagrams/missing.svg")
        )
        found = "\n".join(self.findings())
        self.assertIn("ASSET-009, which is not in the asset registry", found)
        self.assertIn("diagrams/missing.svg, which does not exist", found)


if __name__ == "__main__":
    unittest.main()
