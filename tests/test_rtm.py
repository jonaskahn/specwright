import shutil
import tempfile
import unittest
from pathlib import Path

from kitlib import frontmatter, rtm, schema, workspace

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures/refund/after-spec"


class RtmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "refund"
        shutil.copytree(FIXTURE, self.root)

    def test_orphan_and_empty_bo_survive_rebuild(self):
        rtm.rebuild(self.root, "REF")
        self.assertIn("REF:FEAT-002 orphan: no BO (L-005)", rtm.check(self.root))
        doc = rtm.read_table(self.root / "_meta/rtm.md", rtm.rtm_header())
        self.assertEqual(doc.table.get("REF:FEAT-002", "BO [sw-spec]"), "—")
        self.assertIsNotNone(doc.table.find("REF:AC-002-1"))

    def test_rebuild_preserves_every_cell_and_registry_evidence(self):
        rtm.set_cell(self.root, "REF", "FEAT-001", "Jira", "PROJ-14", "sw-publish")
        path = self.root / "_meta/id-registry.md"
        rtm.registry_upsert(
            path, "REF:FEAT-001", {"Jira key": "PROJ-14", "State": "published"}, "sw-publish"
        )
        before = (self.root / "_meta/rtm.md").read_bytes(), path.read_bytes()
        rtm.rebuild(self.root, "REF")
        self.assertEqual(before, ((self.root / "_meta/rtm.md").read_bytes(), path.read_bytes()))

    def test_reject_ownership_without_writes(self):
        path = self.root / "_meta/rtm.md"
        before = path.read_bytes()
        with self.assertRaises(rtm.OwnershipError):
            rtm.set_cell(self.root, "REF", "FEAT-001", "Jira", "PROJ-14", "shared-trace")
        self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(rtm.OwnershipError):
            rtm.registry_upsert(
                self.root / "_meta/id-registry.md",
                "REF:FEAT-001",
                {"Jira key": "PROJ-14"},
                "sw-spec",
            )
        with self.assertRaises(ValueError):
            rtm.set_cell(self.root, "REF", "FEAT-001", "missing", "x", "qa")
        with self.assertRaises(ValueError):
            rtm.set_cell(self.root, "REF", "FEAT-099", "Test ref", "x", "qa")

    def test_dangling_duplicate_jira_and_tombstone(self):
        path = self.root / "02-drafts/FEAT-001.story.md"
        path.write_text(path.read_text() + "\nSee BR-099.\n")
        for feat in ("FEAT-001", "FEAT-002"):
            rtm.registry_upsert(
                self.root / "_meta/id-registry.md",
                "REF:" + feat,
                {"Jira key": "PROJ-14"},
                "sw-publish",
            )
        path.write_text(
            path.read_text().replace("### AC-001-2 — Duplicate request", "~~AC-001-2~~ withdrawn")
        )
        rtm.rebuild(self.root, "REF")
        findings = "\n".join(rtm.check(self.root))
        self.assertIn("dangling reference: REF:BR-099", findings)
        self.assertIn("L-037", findings)
        self.assertIn("REF:AC-001-2 tombstone", findings)
        self.assertIsNotNone(
            rtm.read_table(self.root / "_meta/rtm.md", rtm.rtm_header()).table.find("REF:AC-001-2")
        )

    def test_impact_includes_criteria_and_jira(self):
        rtm.registry_upsert(
            self.root / "_meta/id-registry.md",
            "REF:FEAT-001",
            {"Jira key": "PROJ-14"},
            "sw-publish",
        )
        result = rtm.impact(self.root, "BO-001", "REF")
        self.assertEqual(result["features"], ["REF:FEAT-001"])
        self.assertEqual(result["criteria"], ["REF:AC-001-1", "REF:AC-001-2"])
        self.assertEqual(result["jira"], ["PROJ-14"])
        self.assertEqual(rtm.impact(self.root, "PROJ-14", "REF")["features"], ["REF:FEAT-001"])
        with self.assertRaises(ValueError):
            rtm.impact(self.root, "BO-099", "REF")

    def test_duplicate_definitions_block_rebuild_and_bad_yaml_fails(self):
        source = self.root / "02-drafts/FEAT-001.story.md"
        duplicate = source.with_name("duplicate.story.md")
        duplicate.write_bytes(source.read_bytes())
        before = (self.root / "_meta/rtm.md").read_bytes()
        self.assertIn("duplicate definition", "\n".join(rtm.check(self.root)))
        with self.assertRaises(ValueError):
            rtm.rebuild(self.root, "REF")
        self.assertEqual(before, (self.root / "_meta/rtm.md").read_bytes())
        duplicate.write_text("---\nid: [broken\n---\n")
        with self.assertRaises(ValueError):
            rtm.scan(self.root)

    def test_cross_scope_resolution_and_snapshot_prose(self):
        root = Path(self.temp.name) / "program"
        workspace.init(root, "program", "REF", "Refunds")
        workspace.init(root, "program", "ORD", "Orders")
        ref = root / "projects/REF"
        order = root / "projects/ORD"
        (order / "01-analysis/BO-001.md").write_text(
            frontmatter.render({"id": "BO-001", "type": "bo"}, "# Outcome\n")
        )
        (ref / "02-drafts/FEAT-001.story.md").write_text(
            frontmatter.render(
                {"id": "FEAT-001", "type": "feature", "bo": ["ORD:BO-001"]},
                "## Acceptance criteria\n### AC-001-1 — Works\nDone.\n",
            )
        )
        (ref / "snapshots/jira/source.md").write_text(
            frontmatter.render(
                {"id": "SRC-0001", "type": "snapshot"}, "FEAT-099 BR-099 are quoted text."
            )
        )
        self.assertEqual(rtm.check(root), [])
        self.assertEqual(rtm.impact(root, "ORD:BO-001", "REF")["features"], ["REF:FEAT-001"])
        self.assertNotIn("REF:FEAT-099", rtm.scan(root)[0])

    def test_historical_rows_are_retained_and_bad_tables_fail(self):
        (self.root / "02-drafts/FEAT-002.story.md").unlink()
        rtm.rebuild(self.root, "REF")
        self.assertIn("historical row", "\n".join(rtm.check(self.root)))
        path = self.root / "_meta/id-registry.md"
        path.write_text("not a table\n")
        with self.assertRaises(ValueError):
            rtm.read_table(path, list(schema.REGISTRY_COLUMNS))


class RegistryColumnTests(unittest.TestCase):
    OLD = schema.REGISTRY_COLUMNS[:9]

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "id-registry.md"
        old = rtm.tables.Table(list(self.OLD))
        old.upsert("REF:FEAT-001", {"Kind": "story", "State": "published"})
        self.path.write_text("# ID registry\n\n" + old.render())

    def test_an_older_registry_is_read_widened_without_loss(self):
        doc = rtm.read_table(self.path, list(schema.REGISTRY_COLUMNS))
        self.assertEqual(doc.table.header, schema.REGISTRY_COLUMNS)
        self.assertEqual(doc.table.get("REF:FEAT-001", "State"), "published")
        self.assertEqual(doc.table.value("REF:FEAT-001", "Title"), "")

    def test_migration_rewrites_once(self):
        self.assertTrue(rtm.migrate_registry(self.path))
        self.assertFalse(rtm.migrate_registry(self.path))
        self.assertIn("Source ref", self.path.read_text())

    def test_shape_may_name_a_reservation_but_not_touch_remote_keys(self):
        rtm.registry_upsert(
            self.path,
            "REF:FEAT-002",
            {"Kind": "story", "Title": "Reset password", "Aliases": "LEG-12"},
            "sw-shape",
        )
        with self.assertRaises(rtm.OwnershipError):
            rtm.registry_upsert(self.path, "REF:FEAT-002", {"Jira key": "PROJ-1"}, "sw-shape")
        doc = rtm.read_table(self.path, list(schema.REGISTRY_COLUMNS))
        self.assertEqual(doc.table.value("REF:FEAT-002", "Aliases"), "LEG-12")

    def test_ingest_owns_snapshot_and_source_ref_only(self):
        cells = {
            "Kind": "snapshot",
            "Last snapshot": "00-inbox/SRC-0001.md",
            "Source ref": "wiki:12",
        }
        rtm.registry_upsert(self.path, "REF:SRC-0001", cells, "sw-ingest")
        with self.assertRaises(rtm.OwnershipError):
            rtm.registry_upsert(self.path, "REF:SRC-0001", {"Confluence id": "9"}, "sw-ingest")
