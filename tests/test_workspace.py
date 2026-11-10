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


if __name__ == "__main__":
    unittest.main()
