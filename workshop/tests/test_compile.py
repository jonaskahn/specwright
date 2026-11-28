"""The heading-feature compiler bundles F04.05 apart from F04.06 and F04.07."""

import re
import unittest
from pathlib import Path

from kitlib import compile as compiler
from kitlib import fm_migrate, hashing

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "workshop/fixtures/compile/SRC-0010.md").read_text()


class CompileTests(unittest.TestCase):
    def test_split_bundles_by_actor_and_screen(self):
        payload = compiler.propose(SOURCE, "SRC-0010")
        bundles = {tuple(item["legacy_ids"]): item for item in payload["bundles"]}
        self.assertEqual(set(bundles), {("F04.05",), ("F04.06", "F04.07")})
        self.assertEqual(bundles[("F04.05",)]["actor"], "a company developer")
        self.assertEqual(bundles[("F04.06", "F04.07")]["page"], "Accounts page")
        self.assertEqual(bundles[("F04.06", "F04.07")]["ac_count"], 4)

    def test_compiled_story_copies_clauses_and_records_gaps(self):
        catalogue = compiler.parse_snapshot(SOURCE, "SRC-0010")
        features = [item for item in catalogue.features if item.legacy_id in ("F04.06", "F04.07")]
        compiled = compiler.render(catalogue, features, "FEAT-218", "GL", "BO-002", [])
        body = compiled.body
        self.assertNotIn("is exercised", body)
        self.assertNotIn("the context of", body)
        self.assertNotIn("When the user selects", body)
        self.assertNotIn("SRC-0030", body)
        self.assertNotIn("2 repositories", body)
        self.assertRegex(body, r"BR-\d{3}:")
        self.assertIn("**When** unanswered (Q-", body)
        self.assertRegex(body, r"SRC-0010:L\d+(?:-L\d+)?#[0-9a-f]{4}")
        self.assertEqual(compiled.fm["legacy_ids"], ["F04.06", "F04.07"])
        self.assertTrue(compiled.fm["br"])
        self.assertFalse(compiled.fm["nfr"])
        self.assertEqual(compiler.coverage_problems(SOURCE, "SRC-0010", compiled.coverage), [])
        for match in re.finditer(
            r"- \*\*Given\*\* (.+)\n- \*\*When\*\* .+\n- \*\*Then\*\* (.+)", body
        ):
            self.assertNotIn(match.group(1), match.group(2))
            self.assertNotIn("Given", match.group(2))

    def test_migration_moves_the_hash_and_refuses_a_mismatch(self):
        story = (
            "---\n"
            "id: FEAT-001\n"
            "type: feature\n"
            "scope: GL\n"
            "title: Check an account\n"
            "aliases: [F04.06]\n"
            "status: draft\n"
            "source_fid: F04.06\n"
            "jira_priority: Medium\n"
            "jira_summary: Check an account\n"
            "epic: [EPIC-004]\n"
            "---\n"
            "## Goal\n\nCheck.\n\n"
            "## Identity\n\nDraft hash: sha256:placeholder\n"
        )
        digest = hashing.draft_hash(story)
        story = story.replace("sha256:placeholder", digest)
        migrated = fm_migrate.migrate_text(story)
        fm = __import__("kitlib.frontmatter", fromlist=["parse"]).parse(migrated).fm
        self.assertEqual(fm["legacy_ids"], ["F04.06"])
        self.assertEqual(fm["priority"], "should")
        self.assertEqual(fm["epic"], "EPIC-004")
        self.assertNotIn("jira_summary", fm)
        self.assertNotIn("source_fid", fm)
        self.assertNotIn("## Identity", migrated)
        self.assertEqual(fm["draft_hash"], hashing.draft_hash(migrated))
        broken = story.replace("Check.", "Changed.")
        with self.assertRaises(fm_migrate.MigrateError):
            fm_migrate.migrate_text(broken)
