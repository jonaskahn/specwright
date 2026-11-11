import importlib.util
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
ASSETS = REPO / "skills/sw-spec/assets"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO / "skills/_shared/scripts"))


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


minify = load_tool("minify")
package = load_tool("package")
from kitlib.borders import find_one_sided  # noqa: E402


class Events(HTMLParser):
    """Tags, attributes and text with whitespace collapsed, so only real changes differ."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events = []
        self.style = False

    def handle_starttag(self, tag, attrs):
        self.events.append(("start", tag, tuple(attrs)))
        self.style = tag == "style"

    def handle_endtag(self, tag):
        self.events.append(("end", tag))
        self.style = False

    def handle_data(self, data):
        if self.style:
            css = re.sub(r"/\*.*?\*/", "", data, flags=re.S)
            text = re.sub(r"\s+", "", css).replace(";}", "}")
        else:
            text = " ".join(data.split())
        if text:
            self.events.append(("data", text))


def flatten(css):
    bare = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.sub(r"\s+", "", bare).replace(";}", "}")


def events(html):
    parser = Events()
    parser.feed(html)
    # Adjacent text pieces differ only by where comments and blank lines were.
    merged = []
    for event in parser.events:
        if merged and event[0] == "data" and merged[-1][0] == "data":
            merged[-1] = ("data", merged[-1][1] + " " + event[1])
        else:
            merged.append(event)
    return merged


class CssTests(unittest.TestCase):
    def test_comments_and_spacing_go(self):
        css = "/* note */\na  >  b {\n  color : red ;\n  margin: 0 auto;\n}\n"
        self.assertEqual(minify.minify_css(css), "a > b{color :red;margin:0 auto}")

    def test_strings_and_urls_are_kept_byte_for_byte(self):
        css = "a{content:\"x  ;  y\";background:url( a b.png );font-family:'A  B'}"
        self.assertEqual(minify.minify_css(css), css)

    def test_calc_operators_keep_their_spaces(self):
        css = "a { width: calc(100% - 2px); height: calc( 1px + 2px ) }"
        self.assertEqual(
            minify.minify_css(css), "a{width:calc(100% - 2px);height:calc( 1px + 2px )}"
        )

    def test_descendant_combinator_is_not_merged(self):
        self.assertEqual(minify.minify_css("a :hover , b:hover { x: y }"), "a :hover,b:hover{x:y}")

    def test_is_idempotent(self):
        once = minify.minify_css("a { b : c ; }\n@media (min-width: 1px) { d { e: f } }")
        self.assertEqual(minify.minify_css(once), once)


class HtmlTests(unittest.TestCase):
    PAGE = (
        "<!doctype html>\n<html>\n  <head>\n    <!-- gone -->\n    <style>\n"
        "      a { color : red ; }\n    </style>\n  </head>\n  <body>\n\n"
        "    <pre>  keep\n      this  </pre>\n"
        "    <script>\n      if (a  <  b) { x(); }\n    </script>\n"
        "    <p>one  two</p>\n  </body>\n</html>\n"
    )

    def test_comments_indent_and_blank_lines_go(self):
        out = minify.minify_html(self.PAGE)
        self.assertNotIn("gone", out)
        self.assertIn("<style>a{color :red}</style>", out)
        self.assertNotIn("\n\n", out)
        self.assertIn("\n<body>\n", out)
        self.assertTrue(out.endswith("</html>\n"))

    def test_pre_and_script_are_untouched(self):
        out = minify.minify_html(self.PAGE)
        self.assertIn("<pre>  keep\n      this  </pre>", out)
        self.assertIn("<script>\n      if (a  <  b) { x(); }\n    </script>", out)

    def test_inner_text_spacing_is_kept(self):
        self.assertIn("<p>one  two</p>", minify.minify_html(self.PAGE))

    def test_is_idempotent(self):
        once = minify.minify_html(self.PAGE)
        self.assertEqual(minify.minify_html(once), once)

    def test_one_element_per_line_is_kept_for_hand_editing(self):
        page = "<svg>\n    <g>\n        <rect x='1'/>\n        <text>a</text>\n    </g>\n</svg>\n"
        self.assertEqual(
            minify.minify_html(page), "<svg>\n<g>\n<rect x='1'/>\n<text>a</text>\n</g>\n</svg>\n"
        )


class ShippedAssetTests(unittest.TestCase):
    def test_every_asset_renders_the_same_after_minifying(self):
        pages = sorted(ASSETS.glob("*.html"))
        self.assertGreater(len(pages), 40)
        for path in pages:
            raw = path.read_text(encoding="utf-8")
            small = minify.minify_html(raw)
            self.assertLess(len(small), len(raw), path.name)
            self.assertEqual(events(small), events(raw), path.name)

    def test_minifying_never_hides_or_creates_one_sided_borders(self):
        for path in sorted(ASSETS.glob("*.html")) + [ASSETS / "theme.css"]:
            raw = path.read_text(encoding="utf-8")
            small = minify.minify_css(raw) if path.suffix == ".css" else minify.minify_html(raw)
            self.assertEqual(
                [m for _, m in find_one_sided(small)],
                [m for _, m in find_one_sided(raw)],
                path.name,
            )

    def test_theme_stylesheet_keeps_every_declaration(self):
        raw = (ASSETS / "theme.css").read_text(encoding="utf-8")
        self.assertEqual(flatten(minify.minify_css(raw)), flatten(raw))


class PackagingTests(unittest.TestCase):
    def test_packaged_html_is_smaller_and_the_source_is_untouched(self):
        before = {p: p.read_bytes() for p in ASSETS.glob("*.html")}
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw) / "dist"
            package.build(REPO, out)
            for source, content in before.items():
                shipped = out / "sw-spec/assets" / source.name
                self.assertLess(shipped.stat().st_size, len(content), source.name)
        self.assertEqual({p: p.read_bytes() for p in ASSETS.glob("*.html")}, before)


if __name__ == "__main__":
    unittest.main()
