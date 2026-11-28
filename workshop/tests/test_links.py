"""Relative links resolve, and fixing a file twice leaves it unchanged."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import links

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sw_links_under_test", ROOT / "skills/_shared/scripts/sw_links.py"
)
sw_links = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sw_links
SPEC.loader.exec_module(sw_links)


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        story = self.base / "features/FEAT-001/FEAT-001.story.md"
        story.parent.mkdir(parents=True)
        story.write_text("---\nid: FEAT-001\ntype: feature\n---\n", encoding="utf-8")
        epic = self.base / "epics/EPIC-001/EPIC-001.md"
        epic.parent.mkdir(parents=True)
        epic.write_text(
            "---\nid: EPIC-001\ntype: epic\n---\n\n## Features\n\n"
            "| ID |\n| --- |\n| FEAT-001 |\n\n## Dependencies and relations\n\nFEAT-001\n",
            encoding="utf-8",
        )
        self.epic = epic

    def test_every_resolved_id_is_a_relative_link(self):
        rendered = links.link_for("FEAT-001", self.epic, self.base)
        self.assertEqual(rendered, "[FEAT-001](../../features/FEAT-001/FEAT-001.story.md)")
        self.assertIsNone(links.link_for("FEAT-999", self.epic, self.base))

    def test_fix_is_idempotent_and_skips_citations(self):
        original = (
            self.epic.read_text(encoding="utf-8") + "Depends on: FEAT-001\nSRC-0001:L2#abcd\n"
        )
        # The citation is not in a dependency section here; Features table and Depends on are.
        once = sw_links.fix_text(original, self.epic, self.base)
        twice = sw_links.fix_text(once, self.epic, self.base)
        self.assertEqual(once, twice)
        self.assertIn("[FEAT-001](../../features/FEAT-001/FEAT-001.story.md)", once)
        self.assertIn("SRC-0001:L2#abcd", once)
