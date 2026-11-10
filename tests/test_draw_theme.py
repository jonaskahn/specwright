"""Measured contrast of the drawing theme tokens (not a WCAG conformance claim)."""

import re
import unittest
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "skills/sw-start/assets/theme.css"


def luminance(color):
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def tokens(block):
    return dict(re.findall(r"--([a-z0-9-]+)\s*:\s*(#[0-9a-f]{6})", block))


class ThemeContrast(unittest.TestCase):
    def test_both_themes_meet_contrast(self):
        text = CSS.read_text(encoding="utf-8")
        light, dark = re.split(
            r"@media\s*\(\s*prefers-color-scheme\s*:\s*dark\s*\)", text, maxsplit=1
        )
        for theme in (tokens(light), tokens(re.split(r"\bbody\s*\{", dark, maxsplit=1)[0])):
            theme = {**tokens(light), **theme}
            for ground in ("sw-bg", "sw-surface"):
                for name in ("sw-ink", "sw-muted", "sw-link", "sw-accent"):
                    self.assertGreaterEqual(ratio(theme[name], theme[ground]), 4.5, (name, ground))
                for name in ("sw-hair", "series-1", "series-2", "series-3", "series-4", "series-5"):
                    self.assertGreaterEqual(ratio(theme[name], theme[ground]), 3.0, (name, ground))

    def test_no_single_side_borders(self):
        self.assertNotRegex(CSS.read_text(encoding="utf-8"), r"border-(left|right|top|bottom)\s*:")


if __name__ == "__main__":
    unittest.main()
