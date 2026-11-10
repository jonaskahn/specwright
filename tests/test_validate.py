import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "validate", Path(__file__).resolve().parent.parent / "tools" / "validate.py"
)
validate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate)

GOOD = (
    "---\nname: sw-demo\n"
    "description: Demonstrates the rules. Use when the user says 'demo'. "
    "Do NOT use for real work (use sw-other).\n"
    'license: MIT\nmetadata:\n  kit: specwright\n  version: "0.1.0"\n---\n'
    "# sw-demo\nRun scripts/run.py. Read references/guide.md when needed.\n"
)


class ValidateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / "lib" / "kitlib").mkdir(parents=True)
        self.skill = self.root / "skills" / "sw-demo"
        (self.skill / "scripts").mkdir(parents=True)
        (self.skill / "references").mkdir()
        (self.skill / "SKILL.md").write_text(GOOD)
        (self.skill / "scripts" / "run.py").write_text(
            "import argparse\nargparse.ArgumentParser().parse_args()\n"
        )
        (self.skill / "references" / "guide.md").write_text("# guide\n")
        evals = self.root / "evals" / "sw-demo"
        evals.mkdir(parents=True)
        rows = [{"query": f"q{i}", "should_trigger": i < 8} for i in range(16)]
        (evals / "triggers.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
        cases = {"cases": [{"id": "a", "prompt": "p", "assertions": ["x"]}]}
        (evals / "cases.json").write_text(json.dumps(cases))

    def run_validate(self):
        report = validate.Report(self.root)
        validate.validate_skill(
            self.skill, self.root / "evals", self.root / "lib" / "kitlib", report
        )
        return report

    def codes(self, report):
        return {f.code for f in report.errors}

    def test_clean_skill_passes(self):
        self.assertEqual(self.run_validate().errors, [])

    def test_unknown_front_matter_key(self):
        (self.skill / "SKILL.md").write_text(
            GOOD.replace("license: MIT", "version: 1\nlicense: MIT")
        )
        self.assertIn("V002", self.codes(self.run_validate()))

    def test_name_must_match_folder_and_prefix(self):
        (self.skill / "SKILL.md").write_text(GOOD.replace("name: sw-demo", "name: other"))
        codes = self.codes(self.run_validate())
        self.assertTrue({"V005", "V006"} <= codes)

    def test_description_rules(self):
        long = GOOD.replace("Demonstrates the rules.", "x" * 1100)
        (self.skill / "SKILL.md").write_text(long)
        self.assertIn("V008", self.codes(self.run_validate()))
        (self.skill / "SKILL.md").write_text(GOOD.replace("Do NOT use", "Avoid"))
        self.assertIn("V011", self.codes(self.run_validate()))

    def test_metadata_values_must_be_strings(self):
        (self.skill / "SKILL.md").write_text(GOOD.replace('"0.1.0"', "3"))
        self.assertIn("V014", self.codes(self.run_validate()))

    def test_missing_reference_target(self):
        (self.skill / "references" / "guide.md").unlink()
        self.assertIn("V024", self.codes(self.run_validate()))

    def test_eval_prose_must_not_live_in_the_body(self):
        (self.skill / "SKILL.md").write_text(GOOD + "\n## Triggers\nstuff\n")
        self.assertIn("V023", self.codes(self.run_validate()))

    def test_script_rules(self):
        (self.skill / "scripts" / "run.py").write_text("import requests\nx = input()\n")
        codes = self.codes(self.run_validate())
        self.assertTrue({"V031", "V032"} <= codes)

    def test_trigger_counts(self):
        path = self.root / "evals" / "sw-demo" / "triggers.jsonl"
        path.write_text(json.dumps({"query": "only", "should_trigger": True}))
        self.assertIn("V044", self.codes(self.run_validate()))

    def test_missing_cases_file(self):
        (self.root / "evals" / "sw-demo" / "cases.json").unlink()
        self.assertIn("V045", self.codes(self.run_validate()))

    def test_vendored_copy_must_match(self):
        (self.root / "lib" / "kitlib" / "a.py").write_text("x = 1\n")
        vendored = self.skill / "scripts" / "kitlib"
        vendored.mkdir()
        (vendored / "a.py").write_text("x = 2\n")
        self.assertIn("V050", self.codes(self.run_validate()))

    def test_missing_skill_file(self):
        (self.skill / "SKILL.md").unlink()
        self.assertIn("V000", self.codes(self.run_validate()))


if __name__ == "__main__":
    unittest.main()
