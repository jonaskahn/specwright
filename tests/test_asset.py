import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import graph, ids, tables

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "skills/sw-asset/scripts/store.py"


class AssetStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        init = subprocess.run(
            [
                sys.executable,
                str(ROOT / "skills/sw-init/scripts/workspace.py"),
                "init",
                "--root",
                str(self.root),
                "--mode",
                "flat",
                "--scope",
                "REF",
                "--name",
                "Refunds",
                "--project-key",
                "PROJ",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(init.returncode, 0, init.stderr)

    def run_store(self, *args):
        return subprocess.run(
            [sys.executable, str(STORE), *args], capture_output=True, text=True, timeout=15
        )

    def test_raw_idea_and_registry(self):
        result = self.run_store(
            "--root", str(self.root), "--kind", "raw-idea", "--text", "one-tap refunds"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        asset_id = result.stdout.split()[0]
        self.assertEqual(asset_id, "ASSET-001")
        self.assertTrue((self.root / "assets" / "ASSET-001.md").is_file())
        registry = tables.parse((self.root / "_meta/asset-registry.md").read_text(encoding="utf-8"))
        self.assertEqual(registry.table.rows[0][0], "ASSET-001")
        self.assertEqual(registry.table.rows[0][2], "raw-idea")
        self.assertEqual(registry.table.rows[0][6], "")

    def test_next_asset_id_never_reuses(self):
        for text in ("first", "second"):
            result = self.run_store("--root", str(self.root), "--kind", "raw-idea", "--text", text)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted((self.root / "assets").glob("ASSET-*.md")).__len__(), 2)
        self.assertTrue((self.root / "assets" / "ASSET-002.md").is_file())

    def test_graph_builds_asset_node(self):
        result = self.run_store(
            "--root", str(self.root), "--kind", "figma", "--text", "https://figma.test/f1"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = graph.build(self.root)
        self.assertTrue(changed)
        found = graph.build_graph(self.root, ["REF"])
        keys = {n.key for n in found.nodes.values()}
        self.assertIn("REF:asset/ASSET-001", keys)
        self.assertTrue(any(n.kind == "asset" for n in found.nodes.values()))
        self.assertFalse(any(e.rel == "supports" for e in found.edges))
        self.assertEqual(ids.next_id("ASSET", []), "ASSET-001")

    def test_graph_supports_edge_from_registry_refs(self):
        self.run_store(
            "--root",
            str(self.root),
            "--kind",
            "figma",
            "--text",
            "https://figma.test/f1",
            "--refs",
            "FEAT-001",
        )
        found = graph.build_graph(self.root, ["REF"])
        self.assertTrue(any(e.rel == "supports" for e in found.edges))


if __name__ == "__main__":
    unittest.main()
