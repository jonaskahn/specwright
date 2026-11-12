"""A command's spec changes are committed, and pushed when a remote is set up. Real git."""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import checkpoint, miniyaml, workspace

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/_shared/scripts/checkpoint.py"
GIT = shutil.which("git")


def git(repo, *args, check=True):
    done = subprocess.run(
        [GIT, "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.test",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.test",
        },
    )
    if check and done.returncode:
        raise AssertionError(done.stderr)
    return done.stdout.strip()


@unittest.skipUnless(GIT, "git is not installed")
class CheckpointTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name).resolve() / "app"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.name", "t")
        git(self.repo, "config", "user.email", "t@example.test")
        git(self.repo, "config", "commit.gpgsign", "false")
        workspace.init(self.repo, "flat", "REF", "Refunds", layout="embedded")
        self.root = self.repo / ".specwright"
        (self.repo / "src.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "start")
        self.remote = Path(tmp.name).resolve() / "remote.git"
        subprocess.run([GIT, "init", "-q", "--bare", "-b", "main", str(self.remote)], check=True)

    def draft(self, name="FEAT-001.story.md", text="# story\n"):
        path = self.root / "02-drafts" / name
        path.write_text(text)
        return path

    def run_commit(self, **kwargs):
        return checkpoint.commit(self.root, "REF", "sw-spec", "FEAT-001 story draft", **kwargs)

    def test_commits_the_spec_files_and_nothing_else(self):
        self.draft()
        (self.repo / "src.py").write_text("x = 2\n")
        result = self.run_commit()
        self.assertEqual((result.status, result.pushed), ("committed", None))
        self.assertEqual(
            git(self.repo, "log", "-1", "--format=%s"), "sw-spec: FEAT-001 story draft"
        )
        self.assertEqual(git(self.repo, "log", "-1", "--format=%b"), "")
        files = git(self.repo, "show", "--name-only", "--format=", "HEAD").splitlines()
        self.assertIn(".specwright/02-drafts/FEAT-001.story.md", files)
        self.assertNotIn("src.py", files)
        self.assertIn("src.py", git(self.repo, "status", "--porcelain"))

    def test_staged_work_outside_the_spec_stays_staged(self):
        self.draft()
        (self.repo / "src.py").write_text("x = 3\n")
        git(self.repo, "add", "src.py")
        self.run_commit()
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "src.py")

    def test_derived_folders_are_not_committed(self):
        self.draft()
        for folder in ("_meta/graph", "_meta/work"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
            (self.root / folder / "x.json").write_text("{}\n")
        (self.root / "_meta/lint-report.md").write_text("report\n")
        self.run_commit()
        files = git(self.repo, "show", "--name-only", "--format=", "HEAD")
        self.assertNotIn("_meta/graph", files)
        self.assertNotIn("_meta/work", files)
        self.assertNotIn("lint-report", files)

    def test_nothing_changed_makes_no_commit(self):
        before = git(self.repo, "rev-parse", "HEAD")
        self.assertEqual(self.run_commit().status, "nothing")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)

    def test_pushes_when_a_remote_is_set_up_and_sets_the_upstream(self):
        git(self.repo, "remote", "add", "origin", str(self.remote))
        self.draft()
        result = self.run_commit()
        self.assertEqual(
            (result.status, result.pushed, result.where), ("committed", True, "origin/main")
        )
        self.assertEqual(git(self.remote, "rev-parse", "main"), git(self.repo, "rev-parse", "HEAD"))
        self.draft(text="# story\nmore\n")
        self.assertTrue(self.run_commit().pushed)
        self.assertEqual(git(self.remote, "rev-parse", "main"), git(self.repo, "rev-parse", "HEAD"))

    def test_without_a_remote_it_only_commits(self):
        self.draft()
        result = self.run_commit()
        self.assertEqual(
            (result.status, result.pushed, result.detail), ("committed", None, "no remote")
        )
        self.assertEqual(result.exit_code, 0)

    def test_commit_mode_and_off_mode_never_push(self):
        git(self.repo, "remote", "add", "origin", str(self.remote))
        self.draft()
        self.assertIsNone(self.run_commit(mode="commit").pushed)
        self.assertEqual(git(self.remote, "branch", "--list"), "")
        self.draft(text="again\n")
        self.assertEqual(self.run_commit(mode="off").status, "off")
        self.assertIn("FEAT-001", git(self.repo, "status", "--porcelain"))

    def test_a_failed_push_keeps_the_commit_and_says_why(self):
        git(self.repo, "remote", "add", "origin", str(self.repo / "missing.git"))
        self.draft()
        result = self.run_commit()
        self.assertEqual((result.status, result.pushed), ("committed", False))
        self.assertEqual(result.exit_code, 4)
        self.assertIn("push failed", result.line())
        self.assertEqual(
            git(self.repo, "log", "-1", "--format=%s"), "sw-spec: FEAT-001 story draft"
        )

    def test_never_forces_a_rejected_push(self):
        git(self.repo, "remote", "add", "origin", str(self.remote))
        self.draft()
        self.run_commit()
        other = self.repo.parent / "other"
        git(self.repo.parent, "clone", "-q", "-b", "main", str(self.remote), str(other))
        git(other, "config", "commit.gpgsign", "false")
        (other / "n.txt").write_text("n\n")
        git(other, "add", "-A")
        git(other, "commit", "-q", "-m", "elsewhere")
        git(other, "push", "-q")
        self.draft(text="# story\nchanged\n")
        result = self.run_commit()
        self.assertEqual((result.status, result.pushed), ("committed", False))
        self.assertNotEqual(
            git(self.remote, "rev-parse", "main"), git(self.repo, "rev-parse", "HEAD")
        )

    def test_a_refusing_hook_blocks_and_is_not_skipped(self):
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\necho no >&2\nexit 1\n")
        hook.chmod(0o755)
        self.draft()
        before = git(self.repo, "rev-parse", "HEAD")
        result = self.run_commit()
        self.assertEqual((result.status, result.exit_code), ("blocked", 3))
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), before)

    def test_waits_while_a_merge_is_open(self):
        (self.repo / ".git/MERGE_HEAD").write_text(git(self.repo, "rev-parse", "HEAD") + "\n")
        self.draft()
        result = self.run_commit()
        self.assertEqual((result.status, result.exit_code), ("busy", 3))

    def test_a_folder_outside_git_is_left_alone(self):
        shutil.rmtree(self.repo / ".git")
        self.draft()
        self.assertEqual(self.run_commit().status, "no-repo")

    def test_long_subjects_are_cut(self):
        self.draft()
        checkpoint.commit(self.root, "REF", "sw-spec", "x" * 200)
        self.assertLessEqual(
            len(git(self.repo, "log", "-1", "--format=%s")), checkpoint.SUBJECT_MAX
        )


@unittest.skipUnless(GIT, "git is not installed")
class ModeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        workspace.init(self.root, "program", "REF", "Refunds")
        workspace.init(self.root, "program", "ORD", "Orders")

    def test_defaults_to_push_and_a_project_overrides_the_program(self):
        self.assertEqual(checkpoint.mode_for(self.root, "REF"), "push")
        checkpoint.set_mode(self.root, None, "commit")
        self.assertEqual(checkpoint.mode_for(self.root, "REF"), "commit")
        checkpoint.set_mode(self.root, "ORD", "off")
        self.assertEqual(checkpoint.mode_for(self.root, "ORD"), "off")
        self.assertEqual(checkpoint.mode_for(self.root, "REF"), "commit")
        data = miniyaml.loads((self.root / "workspace.yaml").read_text())
        self.assertEqual(data["checkpoint"], "commit")
        self.assertEqual(data["projects"], ["REF", "ORD"])

    def test_an_unknown_value_is_refused(self):
        with self.assertRaises(workspace.WorkspaceError):
            checkpoint.set_mode(self.root, "REF", "always")

    def test_the_script_reads_and_sets_the_mode(self):
        spec = importlib.util.spec_from_file_location("checkpoint_cli", SCRIPT)
        cli = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cli
        spec.loader.exec_module(cli)
        self.assertEqual(
            cli.main(["mode", "--cwd", str(self.root), "--scope", "REF", "--set", "off"]), 0
        )
        self.assertEqual(checkpoint.mode_for(self.root, "REF"), "off")
        self.assertEqual(
            cli.main(
                [
                    "commit",
                    "--cwd",
                    str(self.root),
                    "--scope",
                    "REF",
                    "--skill",
                    "sw-spec",
                    "--subject",
                    "x",
                ]
            ),
            0,
        )


if __name__ == "__main__":
    unittest.main()
