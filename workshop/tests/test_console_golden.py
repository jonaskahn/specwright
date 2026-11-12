import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "workshop/tools/gen_console_golden.py"
CONTRACT = ROOT / "workshop/tools/gen_console_contract.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GoldenTests(unittest.TestCase):
    def test_committed_golden_files_match_what_the_python_side_writes(self):
        """The console replays these files, so they must change whenever the format does."""
        golden = load(TOOL, "gen_console_golden")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            golden.generate(out)
            made = sorted(p.relative_to(out) for p in out.rglob("*") if p.is_file())
            kept = golden.OUT
            have = sorted(p.relative_to(kept) for p in kept.rglob("*") if p.is_file())
            self.assertEqual(made, have, "run: python3 workshop/tools/gen_console_golden.py")
            for rel in made:
                self.assertEqual(
                    (out / rel).read_text(),
                    (kept / rel).read_text(),
                    f"{rel} is stale: run python3 workshop/tools/gen_console_golden.py",
                )

    def test_the_contract_covers_every_kind_and_relation(self):
        contract = load(CONTRACT, "gen_console_contract")
        from kitlib import dataformat, schema

        types = contract.typescript()
        for kind in dataformat.KINDS:
            self.assertIn(f"{kind[0].upper()}{kind[1:]}Data", types)
        for rel in schema.RELATIONS:
            self.assertIn(f'"{rel}"', types)
        schema_doc = contract.json_schema()
        self.assertEqual(set(schema_doc["$defs"]), set(dataformat.KINDS))


if __name__ == "__main__":
    unittest.main()
