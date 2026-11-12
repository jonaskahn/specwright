"""A drawn picture is shown in its story, once, and an approved story is never edited."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, hashing, illustration

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "skills/sw-spec/scripts"
spec = importlib.util.spec_from_file_location("embed_diagram", SCRIPTS / "embed_diagram.py")
embed = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = embed
spec.loader.exec_module(embed)

DRAW = (ROOT / "workshop/fixtures/lint/illustration-draw.md").read_text()
APPROVED = frontmatter.update(DRAW, {"status": "ready-to-publish"})
SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><title>Pay</title></svg>\n'
PICTURE = "diagrams/FEAT-009.flow.svg"
ALT = "Payment flow from cashier to seller (AC-009-1, AC-009-2)"


class EmbedTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        (self.base / "02-drafts").mkdir()
        (self.base / "diagrams").mkdir()
        self.story = self.base / "02-drafts/FEAT-009.story.md"
        self.story.write_text(DRAW)
        (self.base / PICTURE).write_text(SVG)
        (self.base / "diagrams/FEAT-009.flow.json").write_text(
            json.dumps({"title": "Pay", "spec_ids": ["AC-009-1", "AC-009-2"]})
        )

    def run_embed(self, picture=PICTURE, alt=ALT):
        return embed.run(self.base, "FEAT-009", picture, alt)

    def test_the_picture_is_listed_embedded_and_the_hash_restamped(self):
        self.run_embed()
        text = self.story.read_text()
        self.assertIn(f"- diagram — {ALT} — {PICTURE}", text)
        self.assertIn(f"![{ALT}](../{PICTURE})", text)
        self.assertIn("Visuals:", text)
        self.assertIn(f"{ALT} — {PICTURE}\n![{ALT}](../{PICTURE})\n\n## Out of scope", text)
        self.assertFalse(hashing.needs_stamp(text))
        result = illustration.state(self.base, "FEAT-009")
        self.assertEqual(result["chip"], illustration.ILLUSTRATED)
        self.assertEqual([p["embedded"] for p in result["pictures"]], [True])
        self.assertEqual(result["broken"], [])

    def test_a_second_run_changes_nothing(self):
        self.run_embed()
        once = self.story.read_text()
        self.run_embed()
        self.assertEqual(self.story.read_text(), once)
        self.assertEqual(once.count(PICTURE), 2)

    def test_a_new_alt_replaces_the_old_lines(self):
        self.run_embed()
        self.run_embed(alt="Payment flow, second reading (AC-009-1)")
        text = self.story.read_text()
        self.assertNotIn(ALT, text)
        self.assertEqual(text.count(PICTURE), 2)

    def test_a_second_picture_joins_the_first(self):
        self.run_embed()
        (self.base / "diagrams/FEAT-009.state.svg").write_text(SVG)
        (self.base / "diagrams/FEAT-009.state.json").write_text(
            json.dumps({"title": "State", "spec_ids": ["AC-009-2"]})
        )
        self.run_embed("diagrams/FEAT-009.state.svg", "Payment states (AC-009-2)")
        result = illustration.state(self.base, "FEAT-009")
        self.assertEqual(len(result["pictures"]), 2)
        self.assertTrue(all(p["embedded"] for p in result["pictures"]))

    def test_an_approved_story_is_refused_and_left_alone(self):
        self.story.write_text(APPROVED)
        with self.assertRaises(embed.Refused):
            self.run_embed()
        self.assertEqual(self.story.read_text(), APPROVED)
        result = illustration.state(self.base, "FEAT-009")
        self.assertEqual([p["embedded"] for p in result["pictures"]], [False])

    def test_inputs_that_do_not_qualify_are_refused(self):
        cases = {
            "diagrams/FEAT-009.flow.html": "svg",
            "../outside.svg": "inside diagrams",
            "diagrams/missing.svg": "does not exist",
        }
        for picture, word in cases.items():
            with self.assertRaisesRegex(ValueError, word):
                self.run_embed(picture)
        (self.base / "diagrams/FEAT-009.flow.json").unlink()
        with self.assertRaisesRegex(ValueError, "JSON spec"):
            self.run_embed()
        self.assertEqual(self.story.read_text(), DRAW)

    def test_a_picture_with_a_script_or_a_link_is_refused(self):
        (self.base / PICTURE).write_text(SVG.replace("<title>", "<script>x()</script><title>"))
        with self.assertRaisesRegex(ValueError, "offline"):
            self.run_embed()
        self.assertEqual(self.story.read_text(), DRAW)

    def test_an_empty_alt_is_refused(self):
        with self.assertRaisesRegex(ValueError, "--alt"):
            self.run_embed(alt="   ")

    def test_exit_codes(self):
        args = ["FEAT-009", PICTURE, "--alt", ALT, "--scope-root", str(self.base)]
        self.assertEqual(embed.main(args), 0)
        self.assertEqual(embed.main(["FEAT-009", "diagrams/nope.svg", *args[2:]]), 1)
        self.story.write_text(APPROVED)
        self.assertEqual(embed.main(args), 3)


if __name__ == "__main__":
    unittest.main()
