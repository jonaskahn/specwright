"""Keep the repository logo offline, named and bounded in its motion."""

import importlib.util
import math
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "logo.svg"
SCRIPTS = ROOT / "skills/sw-draw/scripts"
sys.path.insert(0, str(SCRIPTS))


def module(name):
    spec = importlib.util.spec_from_file_location("logo_" + name, SCRIPTS / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


BORDERS = module("check_borders")
OFFLINE = module("check_offline")
SVG = "{http://www.w3.org/2000/svg}"


class LogoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = LOGO.read_text(encoding="utf-8")
        cls.root = ET.parse(LOGO).getroot()

    def test_logo_is_valid_and_offline(self):
        self.assertEqual(self.root.tag, f"{SVG}svg")
        self.assertEqual(BORDERS.main([str(LOGO)]), 0)
        self.assertEqual(OFFLINE.main([str(LOGO)]), 0)

    def test_logo_names_its_mark_and_motion(self):
        labelled = self.root.get("aria-labelledby", "").split()
        ids = {element.get("id") for element in self.root}
        self.assertEqual(labelled, ["sw-title", "sw-desc"])
        self.assertLessEqual(set(labelled), ids)
        title = self.root.find(f"{SVG}title").text
        desc = self.root.find(f"{SVG}desc").text
        self.assertEqual(title, "Specwright")
        self.assertIn("bullseye dot sits on the ring", desc)
        self.assertIn("travels once around its edge", desc)
        self.assertIn("square marker on the bottom edge", desc)

    def test_motion_is_bounded_and_has_static_fallbacks(self):
        self.assertNotIn("infinite", self.text)
        self.assertRegex(self.text, r"animation:\s*sw-run\s+4s\s+linear\s+1\s+forwards")
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.text)
        self.assertIn("@media print", self.text)
        self.assertGreaterEqual(len(re.findall(r"animation:\s*none", self.text)), 2)
        self.assertIn("#c40e22", self.text)
        self.assertIn("#fd736d", self.text)

    def test_edge_markers_are_centered_on_the_ring(self):
        def by_class(name):
            return next(e for e in self.root.iter() if e.get("class") == name)

        ring = by_class("sw-ring")
        radius = float(ring.get("r"))
        centre = (float(ring.get("cx")), float(ring.get("cy")))
        dot = by_class("sw-marker")
        dot_centre = (float(dot.get("cx")), float(dot.get("cy")))
        self.assertAlmostEqual(math.dist(centre, dot_centre), radius)
        self.assertGreaterEqual(float(dot.get("r")), 8)
        chip = by_class("sw-chip")
        chip_centre = (
            float(chip.get("x")) + float(chip.get("width")) / 2,
            float(chip.get("y")) + float(chip.get("height")) / 2,
        )
        self.assertAlmostEqual(math.dist(centre, chip_centre), radius)


if __name__ == "__main__":
    unittest.main()
