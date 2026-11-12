"""An epic names the business objectives it serves, one or many."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import epics, frontmatter

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "new_epic", ROOT / "skills/sw-shape/scripts/new_epic.py"
)
new_epic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = new_epic
SPEC.loader.exec_module(new_epic)


class EpicObjectiveTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        cards = self.root / "01-analysis"
        cards.mkdir()
        for number in ("001", "002"):
            (cards / f"BO-{number}.md").write_text(f"---\nid: BO-{number}\ntype: bo\n---\n")

    def bo(self, path):
        fm, _ = frontmatter.split(path.read_text())
        return fm["bo"]

    def test_an_epic_lists_several_objectives_without_repeats(self):
        path = new_epic.create(
            self.root, "REF", "Refunds", bo=["BO-001", "ORD:BO-007", "BO-002,BO-001"]
        )
        self.assertEqual(self.bo(path), ["BO-001", "ORD:BO-007", "BO-002"])

    def test_without_objectives_the_list_stays_empty(self):
        self.assertEqual(self.bo(new_epic.create(self.root, "REF", "Refunds")), [])

    def test_an_unknown_or_malformed_objective_is_refused(self):
        with self.assertRaisesRegex(ValueError, "BO-009 is not a business objective"):
            new_epic.create(self.root, "REF", "Refunds", bo=["BO-009"])
        with self.assertRaisesRegex(ValueError, "not a business objective ID"):
            new_epic.create(self.root, "REF", "Refunds", bo=["FEAT-001"])
        self.assertEqual(list((self.root / "01-analysis").glob("epics/*")), [])

    def test_the_objectives_of_an_existing_epic_can_be_replaced(self):
        path = new_epic.create(self.root, "REF", "Refunds", bo=["BO-001"])
        epics.set_objectives(self.root, "REF", "EPIC-001", ["BO-002"])
        self.assertEqual(self.bo(path), ["BO-002"])
        self.assertIn("title: Refunds", path.read_text())
        with self.assertRaisesRegex(ValueError, "EPIC-009 is not an epic"):
            epics.set_objectives(self.root, "REF", "EPIC-009", ["BO-002"])

    def test_the_command_line_takes_repeated_objectives(self):
        code = new_epic.main(
            ["--scope-root", str(self.root), "--scope", "REF", "--title", "T", "--bo", "BO-001"]
        )
        self.assertEqual(code, 0)
        bad = new_epic.main(
            ["--scope-root", str(self.root), "--scope", "REF", "--title", "U", "--bo", "BO-404"]
        )
        self.assertEqual(bad, 1)
        done = new_epic.main(
            [*("--scope-root", str(self.root), "--scope", "REF"), "--set-bo", "EPIC-001"]
            + ["--bo", "BO-002"]
        )
        self.assertEqual(done, 0)


if __name__ == "__main__":
    unittest.main()
