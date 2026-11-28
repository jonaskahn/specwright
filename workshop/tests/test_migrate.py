"""Moving a project from the earlier layout to one folder per item."""

import shutil
import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, migrate, paths, workspace


def write(path: Path, text: str = "x\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def listing(base: Path) -> list[str]:
    return sorted(p.relative_to(base).as_posix() for p in base.rglob("*"))


class MigrateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        fm = {"id": "FEAT-001", "type": "feature"}
        story = frontmatter.render(fm, "see ![x](../diagrams/a.svg)\n")
        write(self.base / "02-drafts/FEAT-001.story.md", story)
        write(self.base / "02-drafts/FEAT-001.card.md")
        write(self.base / "02-drafts/review/FEAT-001.debate.md")
        write(self.base / "01-analysis/epics/EPIC-001--refunds.md")
        write(self.base / "03-plan/FEAT-001.tasks.md")
        write(self.base / "03-plan/FEAT-001.plan.md")
        write(self.base / "03-plan/prompts/FEAT-001/TASK-001-1.md")
        write(self.base / "_meta/id-registry.md")

    def test_every_old_file_has_a_new_home(self):
        moved = {
            s.relative_to(self.base).as_posix(): d.relative_to(self.base).as_posix()
            for s, d in migrate.plan(self.base)
        }
        expected = {
            "02-drafts/FEAT-001.story.md": "features/FEAT-001/FEAT-001.story.md",
            "02-drafts/review/FEAT-001.debate.md": "features/FEAT-001/review/FEAT-001.debate.md",
            "01-analysis/epics/EPIC-001--refunds.md": "epics/EPIC-001/EPIC-001--refunds.md",
            "03-plan/FEAT-001.tasks.md": "tasks/FEAT-001/FEAT-001.tasks.md",
            "03-plan/FEAT-001.plan.md": "plans/FEAT-001/FEAT-001.plan.md",
            "03-plan/prompts/FEAT-001/TASK-001-1.md": "tasks/FEAT-001/prompts/TASK-001-1.md",
            "_meta/id-registry.md": ".metadata/id-registry.md",
        }
        for old, new in expected.items():
            self.assertEqual(moved[old], new)

    def test_planning_changes_nothing(self):
        before = listing(self.base)
        migrate.plan(self.base)
        self.assertEqual(before, listing(self.base))

    def test_applying_moves_files_fixes_links_and_removes_empty_folders(self):
        moved, skipped = migrate.apply(self.base)
        self.assertEqual(len(moved), 8)
        self.assertEqual(skipped, [])
        self.assertIn("](../../diagrams/a.svg)", paths.story(self.base, "FEAT-001").read_text())
        for old in ("02-drafts", "03-plan", "_meta"):
            self.assertFalse((self.base / old).exists(), old)

    def test_running_it_twice_moves_nothing_the_second_time(self):
        migrate.apply(self.base)
        self.assertEqual(migrate.apply(self.base), ([], []))

    def test_an_existing_destination_is_never_overwritten(self):
        write(paths.story(self.base, "FEAT-001"), "newer\n")
        moved, skipped = migrate.apply(self.base)
        self.assertEqual(paths.story(self.base, "FEAT-001").read_text(), "newer\n")
        self.assertEqual([s.name for s, _ in skipped], ["FEAT-001.story.md"])
        self.assertTrue((self.base / "02-drafts/FEAT-001.story.md").is_file())
        self.assertNotIn("FEAT-001.story.md", [s.name for s, _ in moved])

    def test_the_foundation_folder_goes_with_the_foundation_feature(self):
        fm = {"id": "FEAT-002", "type": "feature", "kind": "foundation"}
        write(self.base / "02-drafts/FEAT-002.story.md", frontmatter.render(fm, "x\n"))
        write(self.base / "02-drafts/foundation/Makefile")
        migrate.apply(self.base)
        self.assertTrue((paths.foundation_dir(self.base, "FEAT-002") / "Makefile").is_file())

    def test_upgrade_lists_the_moves_and_applies_them_only_on_request(self):
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(parent, ignore_errors=True))
        root = parent / ".specwright"
        workspace.init(root, "flat", "REF", "Refunds")
        write(root / "02-drafts/FEAT-001.story.md", frontmatter.render({"id": "FEAT-001"}, "x\n"))
        planned = workspace.upgrade(root, "REF", apply=False)
        line = "move 02-drafts/FEAT-001.story.md -> features/FEAT-001/FEAT-001.story.md"
        self.assertIn(line, planned)
        self.assertTrue((root / "02-drafts/FEAT-001.story.md").is_file())
        workspace.upgrade(root, "REF", apply=True)
        self.assertTrue(paths.story(root, "FEAT-001").is_file())
        self.assertFalse((root / "02-drafts").exists())

    def test_numbered_source_folders_move_under_the_unnumbered_names(self):
        write(self.base / "00-inbox/SRC-0001--policy.md", "policy\n")
        write(self.base / "00-inbox/raw/abcd-policy.md", "bytes\n")
        write(self.base / "01-analysis/ideas/IDEA-refunds.md", "idea\n")
        write(self.base / "01-analysis/epics/EPIC-001--refunds.md", "epic\n")
        moved, skipped = migrate.apply(self.base)
        self.assertEqual(skipped, [])
        self.assertTrue((self.base / "sources/SRC-0001--policy.md").is_file())
        self.assertTrue((self.base / "sources/raw/abcd-policy.md").is_file())
        self.assertTrue((self.base / "analysis/ideas/IDEA-refunds.md").is_file())
        self.assertTrue((self.base / "epics/EPIC-001/EPIC-001--refunds.md").is_file())
        self.assertFalse((self.base / "00-inbox").exists())
        self.assertFalse((self.base / "01-analysis").exists())
        self.assertGreaterEqual(len(moved), 4)


if __name__ == "__main__":
    unittest.main()
