"""Code citations, inventory and the gap-table check (kitlib.analysis, kitlib.inventory)."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "_shared" / "scripts"))

from kitlib import analysis, inventory  # noqa: E402

SERVICE = "class S {\n  int W = 30;\n  void r(int d) {\n    if (d > W) throw new X();\n  }\n}\n"
TEST = "class T {\n  @Test\n  void rejects() { assertThrows(X.class, () -> s.r(31)); }\n}\n"


def _table(rows: str) -> str:
    return (
        "---\nkind: analysis\nscope: A\ntarget: x\nstatus: draft\n---\n\n"
        "## Criteria\n\n| # | Criterion | Intended | Actual | Status | Confidence | Notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n" + rows + "\n## Conflicts\n\nNone\n"
    )


class Analysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        (base / "api/src/test").mkdir(parents=True)
        (base / "api/src/S.java").write_text(SERVICE)
        (base / "api/src/test/T.java").write_text(TEST)
        self.roots = {"api": base / "api"}
        self.file = base / "x.analysis.md"

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, rows):
        self.file.write_text(_table(rows))
        return analysis.check(self.file, self.roots)

    def test_cite_and_stale(self):
        c = analysis.cite(self.roots, "api/src/S.java", 2, 4)
        self.assertRegex(c, r"^CODE:api/src/S.java:L2-L4#[0-9a-f]{8}$")
        r = self.check(f"| C-1 | window 30 days | owner | {c} | partial | medium | |\n")
        self.assertEqual(r["findings"], [])
        (self.roots["api"] / "src/S.java").write_text(SERVICE.replace("30", "14"))
        r = self.check(f"| C-1 | window 30 days | owner | {c} | partial | medium | |\n")
        self.assertTrue(any("stale" in f for f in r["findings"]))

    def test_auto_accept_needs_test_or_two_sites(self):
        c = analysis.cite(self.roots, "api/src/S.java", 4)
        t = analysis.cite(self.roots, "api/src/test/T.java", 3)
        r = self.check(
            f"| C-1 | rejects after 30 | owner | {c}; {t} | done | high | |\n"
            f"| C-2 | stores amount | observed | {c} | done | high | |\n"
        )
        self.assertEqual(r["auto_accepted"], ["C-1"])
        self.assertEqual([a["row"] for a in r["ask"]], ["C-2"])
        self.assertEqual(r["shape"], "as-is")

    def test_rules(self):
        r = self.check(
            "| C-1 | x | SRC-0001:L3 | None | done | high | |\n"
            "| C-2 | y | owner | None | divergent | low | |\n"
            "| C-3 | z | nowhere | None | missing | low | |\n"
        )
        text = " ".join(r["findings"])
        self.assertIn("C-1: done needs at least one CODE citation", text)
        self.assertIn("C-2: divergent needs a Q-NNN or ASK-n", text)
        self.assertIn("C-3: Intended needs", text)

    def test_shapes(self):
        r = self.check("| C-1 | x | owner | None | missing | medium | |\n")
        self.assertEqual(r["shape"], "new")
        c = analysis.cite(self.roots, "api/src/S.java", 2)
        r = self.check(
            f"| C-1 | x | owner | {c} | done | medium | |\n"
            "| C-2 | y | owner | None | missing | low | |\n"
        )
        self.assertEqual(r["shape"], "complete")


class Inventory(unittest.TestCase):
    def test_spring_next_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src/RefundController.java").write_text(
                '@RequestMapping("/api/refunds")\nclass C {\n  @PostMapping("")\n  void a() {}\n}\n'
            )
            (root / "src/Refund.java").write_text("@Entity\npublic class Refund {}\n")
            (root / "app/refunds").mkdir(parents=True)
            (root / "app/refunds/page.tsx").write_text("export default function P() {}\n")
            code = {"r": inventory.scan_code(root, "r")}
            self.assertEqual(code["r"]["endpoints"][0]["name"], "POST /api/refunds")
            self.assertEqual(code["r"]["entities"][0]["name"], "Refund")
            self.assertIn("/refunds", [s["name"] for s in code["r"]["screens"]])
            self.assertEqual(inventory.candidates(code, [])[0]["name"], "refund")


if __name__ == "__main__":
    unittest.main()
