"""The illustration chip is computed, never stored, except for a dismissal in front matter."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, graph, graph_query, hashing, illustration

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "workshop/fixtures"
DRAW = (FIXTURES / "lint/illustration-draw.md").read_text()
PROSE = (FIXTURES / "lint/illustration-prose.md").read_text()
UNSURE = (FIXTURES / "lint/illustration-unsure.md").read_text()
GOOD = (FIXTURES / "lint/good-story.md").read_text()
SCRIPT = ROOT / "skills/sw-spec/scripts/illustration_check.py"
CURRENT = FIXTURES / "refund/illustration/current.json"
STALE = FIXTURES / "refund/illustration/stale.json"


class SignalTests(unittest.TestCase):
    def test_a_multi_actor_branching_story_draws(self):
        signals = illustration.count_signals(DRAW)
        self.assertEqual(
            (
                signals.actors,
                signals.branches,
                signals.state_changes,
                signals.handoffs,
                signals.data_moves,
            ),
            (3, 3, 2, 1, 3),
        )
        self.assertEqual(illustration.verdict(signals), illustration.DRAW)
        self.assertEqual(len(signals.fired()), 5)

    def test_one_actor_and_fewer_than_five_items_is_prose(self):
        signals = illustration.count_signals(PROSE)
        self.assertEqual(signals.actors, 1)
        self.assertLess(signals.items, 5)
        self.assertEqual(illustration.verdict(signals), illustration.PROSE)
        # The canonical lint story is the same shape: one buyer, a short list.
        good = illustration.count_signals(GOOD)
        self.assertEqual(good.actors, 1)
        self.assertLess(good.items, 5)
        self.assertEqual(illustration.verdict(good), illustration.PROSE)

    def test_two_signals_on_a_short_list_are_unsure(self):
        signals = illustration.count_signals(UNSURE)
        self.assertEqual((signals.actors, signals.branches, signals.items), (2, 1, 3))
        self.assertEqual(len(signals.fired()), 2)
        self.assertEqual(illustration.verdict(signals), illustration.UNSURE)

    def test_the_reference_lists_the_words_the_counter_uses(self):
        text = (ROOT / "skills/sw-spec/references/illustration-need.md").read_text()
        for word in (
            *illustration.ROLES,
            *illustration.BRANCH_WORDS,
            *illustration.STATE_VERBS,
            *illustration.DATA_WORDS,
        ):
            self.assertIn(word, text, word)


class ChipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.drafts = self.base / "02-drafts"
        self.drafts.mkdir()

    def write_story(self, text, name="FEAT-009.story.md"):
        path = self.drafts / name
        path.write_text(text)
        return path

    def test_no_picture_uses_the_verdict(self):
        self.write_story(DRAW)
        self.write_story(PROSE, "FEAT-004.story.md")
        self.write_story(UNSURE, "FEAT-005.story.md")
        self.assertEqual(illustration.state(self.base, "FEAT-009")["chip"], illustration.NEEDS)
        self.assertEqual(illustration.state(self.base, "FEAT-004")["chip"], illustration.NONE)
        self.assertEqual(illustration.state(self.base, "FEAT-005")["chip"], illustration.CHECK)

    def test_a_current_picture_is_illustrated_and_a_missing_id_is_check(self):
        self.write_story(
            DRAW.replace("FEAT-009", "FEAT-001").replace("AC-009-", "AC-001-"),
            "FEAT-001.story.md",
        )
        diagrams = self.base / "diagrams"
        diagrams.mkdir()
        current = diagrams / "flow.json"
        shutil.copy(CURRENT, current)
        result = illustration.state(self.base, "FEAT-001")
        self.assertEqual(result["chip"], illustration.ILLUSTRATED)
        self.assertEqual(result["stale"], [])
        shutil.copy(STALE, current)
        stale = illustration.state(self.base, "FEAT-001")
        self.assertEqual(stale["chip"], illustration.CHECK)
        self.assertEqual(stale["stale"], ["REF:AC-001-3"])

    def test_a_fresh_graph_reports_the_same_chip_as_the_json(self):
        root = self.base / "refund"
        shutil.copytree(FIXTURES / "refund/after-spec", root)
        shutil.copy(CURRENT, root / "diagrams/flow.json")
        before = illustration.state(root, "FEAT-001")
        self.assertEqual(before["chip"], illustration.ILLUSTRATED)
        graph.build(root, "REF")
        after = illustration.state(root, "FEAT-001")
        self.assertEqual(after["chip"], illustration.ILLUSTRATED)
        self.assertEqual(after["stale"], [])
        shutil.copy(STALE, root / "diagrams/flow.json")
        graph.build(root, "REF")
        checked = illustration.state(root, "FEAT-001")
        self.assertEqual(checked["chip"], illustration.CHECK)
        self.assertIn("REF:AC-001-3", checked["stale"])

    def test_a_diagram_node_opens_its_svg_and_cites_from_the_json(self):
        root = self.base / "refund"
        shutil.copytree(FIXTURES / "refund/after-spec", root)
        shutil.copy(CURRENT, root / "diagrams/flow.json")
        graph.build(root, "REF")
        store = graph_query.Store(root, "REF")
        self.assertTrue(store.node("REF:diagram/flow")["loc"].startswith("diagrams/flow.json"))
        (root / "diagrams/flow.svg").write_text("<svg/>\n")
        self.assertNotEqual(graph_query.Store(root, "REF").freshness(), "fresh")
        graph.build(root, "REF")
        store = graph_query.Store(root, "REF")
        self.assertTrue(store.node("REF:diagram/flow")["loc"].startswith("diagrams/flow.svg"))
        edges = [e for e in store.edges("out") if e.rel == "illustrates"]
        self.assertTrue(edges)
        self.assertEqual({e.file for e in edges}, {"diagrams/flow.json"})

    def test_dismissal_changes_only_front_matter_and_keeps_the_draft_hash(self):
        path = self.write_story(DRAW)
        before = path.read_text()
        digest = hashing.draft_hash(before)
        body = frontmatter.parse(before).body
        result = illustration.dismiss(
            self.base, "FEAT-009", "single actor, linear flow, five lines"
        )
        after = path.read_text()
        self.assertEqual(result["chip"], illustration.NONE)
        self.assertTrue(result["dismissed"])
        self.assertEqual(frontmatter.parse(after).body, body)
        self.assertEqual(hashing.draft_hash(after), digest)
        self.assertNotEqual(after, before)
        fm = frontmatter.parse(after).fm
        self.assertEqual(fm["illustration"], "none")
        self.assertEqual(fm["illustration_reason"], "single actor, linear flow, five lines")

    def test_a_blank_dismissal_is_refused(self):
        self.write_story(DRAW)
        with self.assertRaises(ValueError):
            illustration.dismiss(self.base, "FEAT-009", "   ")


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        drafts = self.base / "02-drafts"
        drafts.mkdir()
        (drafts / "FEAT-009.story.md").write_text(DRAW)

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_the_command_prints_the_chip_and_can_dismiss(self):
        shown = self.run_cli("FEAT-009", "--scope-root", str(self.base))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("needs illustration", shown.stdout)
        self.assertIn("verdict: DRAW", shown.stdout)
        saved = self.run_cli("FEAT-009", "--scope-root", str(self.base), "--json")
        self.assertEqual(saved.returncode, 0, saved.stderr)
        written = self.base / "_meta/work/illustration-FEAT-009.json"
        self.assertTrue(written.is_file())
        self.assertEqual(json.loads(written.read_text())["chip"], "needs illustration")
        dismissed = self.run_cli(
            "FEAT-009",
            "--scope-root",
            str(self.base),
            "--dismiss",
            "single actor, linear flow, five lines",
        )
        self.assertEqual(dismissed.returncode, 0, dismissed.stderr)
        self.assertIn("no illustration", dismissed.stdout)
        story = (self.base / "02-drafts/FEAT-009.story.md").read_text()
        self.assertEqual(hashing.draft_hash(story), hashing.draft_hash(DRAW))

    def test_usage_and_missing_files_exit_2(self):
        self.assertEqual(self.run_cli().returncode, 2)
        missing = self.run_cli("FEAT-008", "--scope-root", str(self.base))
        self.assertEqual(missing.returncode, 2)
        blank = self.run_cli("FEAT-009", "--scope-root", str(self.base), "--dismiss", " ")
        self.assertEqual(blank.returncode, 2)
