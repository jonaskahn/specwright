import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from kitlib import miniyaml, schema, tables, workspace


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()


class FlatTests(WorkspaceTestCase):
    def init_flat(self):
        return workspace.init(
            self.root,
            "flat",
            "REF",
            "Refunds",
            "example.atlassian.net",
            "PROJ",
            approvers=[{"role": "PO", "name": "Lan Nguyen", "account_id": "712020:aa11"}],
        )

    def test_init_creates_manifest_tree_and_meta_files(self):
        created = self.init_flat()
        self.assertIn("project.yaml", created)
        manifest = miniyaml.loads((self.root / "project.yaml").read_text())
        self.assertEqual(manifest["scope"], "REF")
        self.assertIs(manifest["publish"]["transitions"], False)
        self.assertIs(manifest["publish"]["sandbox"], True)
        self.assertEqual(manifest["approvers"][0]["account_id"], "712020:aa11")
        for folder in (
            "00-inbox",
            "01-analysis",
            "02-drafts",
            "diagrams",
            "records",
            "snapshots",
            "_meta",
        ):
            self.assertTrue((self.root / folder).is_dir(), folder)
        registry = tables.parse((self.root / "_meta" / "id-registry.md").read_text())
        self.assertEqual(registry.table.header, schema.REGISTRY_COLUMNS)
        self.assertEqual(registry.table.rows, [])
        rtm = tables.parse((self.root / "_meta" / "rtm.md").read_text())
        self.assertEqual(rtm.table.header[0], "Spec ID")
        self.assertIn("Jira [sw-publish]", rtm.table.header)

    def test_upgrade_adds_registry_columns_only_on_apply(self):
        self.init_flat()
        path = self.root / "_meta/id-registry.md"
        old = tables.Table(schema.REGISTRY_COLUMNS[:9])
        old.upsert("REF:FEAT-001", {"Kind": "story"})
        path.write_text("# ID registry\n\n" + old.render())
        plan = workspace.upgrade(self.root, "REF")
        self.assertTrue(any("id-registry.md" in line for line in plan))
        self.assertEqual(len(tables.parse(path.read_text()).table.header), 9)
        workspace.upgrade(self.root, "REF", apply=True)
        table = tables.parse(path.read_text()).table
        self.assertEqual(table.header, schema.REGISTRY_COLUMNS)
        self.assertEqual(table.get("REF:FEAT-001", "Kind"), "story")

    def test_new_manifest_has_sources_evidence_and_ignore_folders(self):
        self.init_flat()
        data = miniyaml.loads((self.root / "project.yaml").read_text())
        self.assertEqual(data["sources"], [])
        self.assertEqual(
            data["evidence"]["allowed_kinds"], ["url", "ticket", "document", "meeting"]
        )
        self.assertEqual(
            workspace.evidence_kinds(self.root, "REF"), data["evidence"]["allowed_kinds"]
        )

    def test_approvers_are_added_once_and_blank_values_are_refused(self):
        self.init_flat()
        workspace.add_approver(self.root, "REF", "BA", "An Tran", "712020:bb22")
        self.assertEqual(
            [a["name"] for a in workspace.approver_list(self.root, "REF")],
            ["Lan Nguyen", "An Tran"],
        )
        for bad in (
            ("BA", "", "x:1"),
            ("", "N", "x:1"),
            ("BA", "TBD", "x:1"),
            ("BA", "N", "unknown"),
        ):
            with self.assertRaises(workspace.WorkspaceError):
                workspace.add_approver(self.root, "REF", *bad)
        with self.assertRaises(workspace.WorkspaceError):
            workspace.add_approver(self.root, "REF", "PO", "Lan", "712020:aa11")

    def test_source_registry_validates_and_round_trips(self):
        self.init_flat()
        pattern = r"^LEG-\d{3}$"
        workspace.add_source(
            self.root, "REF", "wiki-1", "confluence", "SPACE/Home", "2026-11-01", 104, pattern
        )
        found = workspace.source_list(self.root, "REF")
        self.assertEqual(
            found,
            [
                {
                    "id": "wiki-1",
                    "system": "confluence",
                    "root": "SPACE/Home",
                    "snapshot_date": "2026-11-01",
                    "expected_count": 104,
                    "legacy_id_pattern": pattern,
                }
            ],
        )
        cases = [
            ("Wiki 1", "c", "r", "2026-11-01", 1, ""),
            ("wiki-2", "", "r", "2026-11-01", 1, ""),
            ("wiki-2", "c", "r", "01/11/2026", 1, ""),
            ("wiki-2", "c", "r", "2026-11-01", -1, ""),
            ("wiki-2", "c", "r", "2026-11-01", 1, "("),
            ("wiki-1", "c", "r", "2026-11-01", 1, ""),
        ]
        for case in cases:
            with self.assertRaises(workspace.WorkspaceError, msg=case):
                workspace.add_source(self.root, "REF", *case)

    def test_upgrade_adds_the_new_manifest_sections(self):
        self.init_flat()
        path = self.root / "project.yaml"
        data = miniyaml.loads(path.read_text())
        for field in ("sources", "evidence", "ignore_folders"):
            del data[field]
        path.write_text(miniyaml.dumps(data))
        plan = workspace.upgrade(self.root, "REF", apply=True)
        self.assertEqual(sum("project.yaml: add" in line for line in plan), 3)
        self.assertEqual(miniyaml.loads(path.read_text())["sources"], [])

    def test_init_makes_import_and_work_folders_and_ignores_the_work_folder(self):
        self.init_flat()
        self.assertTrue((self.root / "00-inbox/imports").is_dir())
        self.assertTrue((self.root / "01-analysis/candidates").is_dir())
        self.assertEqual((self.root / "_meta/work/.gitignore").read_text(), "*\n!.gitignore\n")
        self.assertFalse((self.root / "_meta/work/.gitkeep").exists())

    def test_stray_folders_are_reported_but_known_and_hidden_ones_are_not(self):
        self.init_flat()
        self.assertEqual(workspace.stray_folders(self.root), [])
        for name in ("scratch", "old-notes", ".git", "node_modules", "skills", ".hidden"):
            (self.root / name).mkdir(exist_ok=True)
        (self.root / "README.md").write_text("a file, not a folder")
        self.assertEqual(workspace.stray_folders(self.root), ["old-notes", "scratch"])
        self.assertEqual(workspace.stray_folders(self.root, ["scratch/"]), ["old-notes"])

    def test_upgrade_adds_the_new_folders_to_an_older_workspace(self):
        self.init_flat()
        import shutil

        shutil.rmtree(self.root / "_meta/work")
        shutil.rmtree(self.root / "00-inbox/imports")
        plan = workspace.upgrade(self.root, "REF", apply=True)
        self.assertIn("create _meta/work/", plan)
        self.assertTrue((self.root / "_meta/work/.gitignore").is_file())
        self.assertTrue((self.root / "00-inbox/imports/.gitkeep").is_file())

    def test_init_refuses_to_overwrite(self):
        self.init_flat()
        with self.assertRaises(workspace.WorkspaceError):
            self.init_flat()

    def test_invalid_scope_is_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.init(self.root, "flat", "ref", "x")

    def test_program_init_does_not_convert_a_flat_workspace(self):
        self.init_flat()
        with self.assertRaises(workspace.WorkspaceError):
            workspace.init(self.root, "program", "ORD", "Orders")
        self.assertFalse((self.root / "workspace.yaml").exists())

    def test_no_manifest_means_no_mode(self):
        self.assertEqual(workspace.mode_of(self.root), "none")

    def test_path_traversal_scope_is_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.scope_dir(self.root, "../../outside")

    def test_detect_and_resolve_in_flat_mode(self):
        self.assertEqual(workspace.detect(self.root)["mode"], "none")
        self.init_flat()
        info = workspace.detect(self.root / "02-drafts")
        self.assertEqual((info["mode"], info["scopes"]), ("flat", ["REF"]))
        self.assertEqual(
            workspace.resolve(self.root, cwd=self.root / "02-drafts", write=True), "REF"
        )
        self.assertEqual(workspace.scope_dir(self.root, "REF"), self.root)


class ProgramTests(WorkspaceTestCase):
    def setUp(self):
        super().setUp()
        workspace.init(self.root, "program", "REF", "Refunds")
        workspace.init(self.root, "program", "ORD", "Orders")

    def test_manifest_lists_projects_and_default(self):
        data = miniyaml.loads((self.root / "workspace.yaml").read_text())
        self.assertEqual(data["projects"], ["REF", "ORD"])
        self.assertEqual(data["default_scope"], "REF")
        self.assertTrue((self.root / "projects" / "ORD" / "project.yaml").is_file())

    def test_duplicate_scope_is_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.init(self.root, "program", "REF", "Again")

    def test_existing_project_does_not_partially_update_program_manifest(self):
        before = (self.root / "workspace.yaml").read_bytes()
        orphan = self.root / "projects" / "PAY"
        orphan.mkdir()
        (orphan / "project.yaml").write_text("scope: PAY\n")
        with self.assertRaises(workspace.WorkspaceError):
            workspace.init(self.root, "program", "PAY", "Payments")
        self.assertEqual((self.root / "workspace.yaml").read_bytes(), before)

    def test_root_is_found_from_a_nested_project_folder(self):
        nested = self.root / "projects" / "ORD" / "02-drafts"
        self.assertEqual(workspace.find_root(nested), self.root)

    def test_resolution_order(self):
        nested = self.root / "projects" / "ORD" / "02-drafts"
        self.assertEqual(workspace.resolve(self.root, arg="REF", cwd=nested), "REF")
        self.assertEqual(workspace.resolve(self.root, ref="REF:FEAT-001", cwd=nested), "REF")
        self.assertEqual(workspace.resolve(self.root, cwd=nested, write=True), "ORD")
        self.assertEqual(workspace.resolve(self.root, cwd=self.root), "REF")

    def test_writes_never_use_the_default_scope(self):
        with self.assertRaises(workspace.AskUser) as ctx:
            workspace.resolve(self.root, cwd=self.root, write=True)
        self.assertEqual(ctx.exception.options, ["REF", "ORD"])

    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(workspace.WorkspaceError):
            workspace.resolve(self.root, arg="NOPE")


class CommandLineTests(WorkspaceTestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = workspace.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_needs_choice_exits_with_three(self):
        workspace.init(self.root, "program", "REF", "R")
        workspace.init(self.root, "program", "ORD", "O")
        code, _, err = self.run_cli("resolve", "--cwd", str(self.root), "--write")
        self.assertEqual(code, workspace.EXIT_ASK)
        self.assertIn("REF", err)

    def test_init_then_detect(self):
        code, out, _ = self.run_cli(
            "init",
            "--root",
            str(self.root),
            "--mode",
            "flat",
            "--scope",
            "REF",
            "--name",
            "R",
            "--approver",
            "PO|Lan|712020:aa11",
        )
        self.assertEqual(code, 0)
        self.assertIn("project.yaml", out)
        code, out, _ = self.run_cli("detect", "--cwd", str(self.root))
        self.assertIn('"flat"', out)

    def test_missing_workspace_exits_with_error(self):
        code, _, err = self.run_cli("resolve", "--cwd", str(self.root))
        self.assertEqual(code, workspace.EXIT_ERROR)
        self.assertIn("init", err)

    def test_bad_approver_is_reported(self):
        code, _, err = self.run_cli(
            "init",
            "--root",
            str(self.root),
            "--mode",
            "flat",
            "--scope",
            "REF",
            "--name",
            "R",
            "--approver",
            "only-two|parts",
        )
        self.assertEqual(code, workspace.EXIT_ERROR)
        self.assertIn("approver", err)

    def test_cli_adds_and_lists_approvers_and_sources(self):
        workspace.init(self.root, "flat", "REF", "Refunds")
        where = ["--cwd", str(self.root)]
        code, out, _ = self.run_cli(
            "approvers", "add", "--role", "BA", "--name", "An", "--account-id", "9:z", *where
        )
        self.assertEqual(code, 0)
        self.assertIn("An", out)
        code, _, err = self.run_cli("approvers", "add", "--role", "BA", *where)
        self.assertEqual(code, workspace.EXIT_ERROR)
        self.assertIn("needs a real", err)
        code, out, _ = self.run_cli(
            "source",
            "add",
            "--id",
            "wiki",
            "--system",
            "confluence",
            "--root",
            "S/H",
            "--snapshot-date",
            "2026-11-01",
            "--expected-count",
            "3",
            *where,
        )
        self.assertEqual(code, 0)
        self.assertIn('"expected_count": 3', out)


if __name__ == "__main__":
    unittest.main()
