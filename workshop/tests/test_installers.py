"""Exercise real shell/PowerShell upgrades against isolated installs, never the user's home."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.support import put

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ("sw-start", "sw-craft", "sw-forge", "sw-ship", "sw-view")
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


class InstallerCases:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / "source"
        self.target = self.base / "project"
        self.target.mkdir()
        self.home = self.base / "home"
        self.home.mkdir()
        self.bin = self.base / "bin"
        self.bin.mkdir()
        for skill in SKILLS:
            put(self.source / f"skills/{skill}/SKILL.md", f"---\nname: {skill}\n---\nnew\n")
            put(self.source / f"skills/{skill}/_shared/new.py", "new")
            put(
                self.source / f"commands/{skill}.md",
                f"---\nname: {skill}\n---\nLoad ${{CLAUDE_PLUGIN_ROOT}}/skills/{skill}/SKILL.md\n",
            )
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("SPECWRIGHT_")}
        self.env.update(
            {
                "SPECWRIGHT_ROOT": str(self.source),
                "HOME": str(self.home),
                "USERPROFILE": str(self.home),
                "XDG_CONFIG_HOME": str(self.home / ".config"),
                "NO_COLOR": "1",
                "PATH": str(self.bin) + os.pathsep + os.environ["PATH"],
            }
        )

    @property
    def skills(self):
        return self.target / ".agents/skills"

    def seed(self):
        for skill in (*SKILLS, "sw-spec", "sw-review", "sw-analyze"):
            put(self.skills / skill / "SKILL.md", f"---\nname: {skill}\n---\nold\n")
            put(self.skills / skill / "_shared/stale.py", "stale")
        put(
            self.target / ".agents/commands/sw-spec.md",
            "name: sw-spec\nLoad /old/skills/sw-spec/SKILL.md\n",
        )
        put(self.target / ".agents/commands/custom.md", "keep")
        put(self.skills / "custom/SKILL.md", "keep")
        put(self.target / ".specwright/keep.md", "keep")

    def assert_new(self):
        self.assertEqual(sorted(p.name for p in self.skills.glob("sw-*")), sorted(SKILLS))
        for skill in SKILLS:
            self.assertTrue((self.skills / skill / "_shared/new.py").is_file())
            self.assertFalse((self.skills / skill / "_shared/stale.py").exists())
            command = self.target / f".agents/commands/{skill}.md"
            self.assertIn(self.skills.as_posix() + "/", command.read_text())
        self.assertFalse((self.target / ".agents/commands/sw-spec.md").exists())
        self.assertEqual((self.target / ".agents/commands/custom.md").read_text(), "keep")
        self.assertEqual((self.skills / "custom/SKILL.md").read_text(), "keep")
        self.assertEqual((self.target / ".specwright/keep.md").read_text(), "keep")
        self.assertFalse(list(self.target.rglob(".specwright-backup*")))

    def test_upgrade_and_repeated_install_leave_only_new_files(self):
        self.seed()
        for _ in range(2):
            result = self.run_install()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assert_new()

    def test_invalid_source_does_not_remove_old_files(self):
        self.seed()
        (self.source / "skills/sw-view/SKILL.md").unlink()
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.skills / "sw-spec/_shared/stale.py").is_file())

    def test_output_has_one_install_summary_without_per_destination_logs(self):
        self.seed()
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("Installed 5 skills in 1 location(s)"), 1)
        self.assertIn("Run /sw-start to begin.", result.stdout)
        for verbose in (
            "Copied ",
            "Linked ",
            "Removed the previous install",
            "Replacing ",
            self.skills.as_posix(),
            "Your next step",
        ):
            self.assertNotIn(verbose, result.stdout)

    def test_every_sw_prefixed_file_folder_and_link_is_removed(self):
        self.seed()
        put(self.skills / "sw-unknown/SKILL.md", "not a Specwright skill")
        put(self.skills / "sw-partial", "incomplete file")
        put(self.target / ".agents/commands/sw-partial/cache", "incomplete folder")
        put(self.target / ".agents/commands/sw-old.txt", "old")
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_new()
        self.assertFalse((self.target / ".agents/commands/sw-partial").exists())
        self.assertFalse((self.target / ".agents/commands/sw-old.txt").exists())

    def test_failed_copy_restores_all_old_files(self):
        self.seed()
        result = self.run_install(fail_copy=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        for skill in (*SKILLS, "sw-spec", "sw-review", "sw-analyze"):
            self.assertEqual((self.skills / skill / "_shared/stale.py").read_text(), "stale")
        self.assertTrue((self.target / ".agents/commands/sw-spec.md").exists())
        self.assertFalse(list(self.target.rglob(".specwright-backup*")))


@unittest.skipIf(os.name == "nt", "POSIX shell installer")
class ShellInstallTests(InstallerCases, unittest.TestCase):
    def run_install(self, fail_copy=False):
        if fail_copy:
            cp = shutil.which("cp")
            shim = put(
                self.bin / "cp",
                f'#!/bin/sh\ncase "$*" in *"{self.skills}/sw-forge"*) exit 1;; esac\n'
                f'exec "{cp}" "$@"\n',
            )
            shim.chmod(0o755)
        return subprocess.run(
            [
                "sh",
                str(ROOT / "install.sh"),
                "--project",
                "--target",
                str(self.target),
                "--agent",
                "universal",
                "-y",
            ],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_dangling_and_external_skill_links_are_replaced_without_touching_target(self):
        self.seed()
        external = self.base / "external"
        put(external / "SKILL.md", "name: sw-legacy\n")
        put(external / "keep", "keep")
        (self.skills / "sw-legacy").symlink_to(external, target_is_directory=True)
        (self.skills / "sw-dangling").symlink_to(self.base / "absent", target_is_directory=True)
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_new()
        self.assertEqual((external / "keep").read_text(), "keep")

    def test_direct_migration_cleans_all_sw_entries_in_paths_with_spaces(self):
        target = self.base / "skills with spaces"
        put(target / "sw-broken/stale", "old")
        put(target / "sw-file", "old")
        put(self.base / "commands/sw-retired.txt", "old")
        put(target / "custom/keep", "keep")
        result = subprocess.run(
            ["sh", str(ROOT / "migrate.sh"), "--yes", "--no-backup", str(target)],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sorted(p.name for p in target.glob("sw-*")), sorted(SKILLS))
        self.assertFalse((self.base / "commands/sw-retired.txt").exists())
        self.assertIn(str(target) + "/", (self.base / "commands/sw-start.md").read_text())
        self.assertEqual((target / "custom/keep").read_text(), "keep")


@unittest.skipUnless(POWERSHELL, "PowerShell unavailable; Windows CI runs these cases")
class PowerShellInstallTests(InstallerCases, unittest.TestCase):
    def run_install(self, fail_copy=False):
        def quote(value):
            return "'" + str(value).replace("'", "''") + "'"

        prefix = ""
        if fail_copy:
            prefix = (
                "function Copy-Item { param($LiteralPath, $Destination, [switch]$Recurse) "
                f"if ($Destination -eq {quote(self.skills / 'sw-forge')}) "
                "{ throw 'simulated copy failure' }; "
                "Microsoft.PowerShell.Management\\Copy-Item -LiteralPath $LiteralPath "
                "-Destination $Destination -Recurse:$Recurse }; "
            )
        command = (
            prefix + f"& {quote(ROOT / 'install.ps1')} -Project -Target {quote(self.target)} "
            "-Agent universal -Yes"
        )
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=self.base,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )
