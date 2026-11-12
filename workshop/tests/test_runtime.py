import hashlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kitlib import runtime

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/_shared/scripts/runtime.sh"
PINS = ROOT / "skills/_shared/scripts/runtime-pins.tsv"
HOOKS = ROOT / "hooks/hooks.json"
START = ROOT / "skills/sw-start/scripts/start.py"
PLATFORMS = {"darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64", "win-x64"}
TOOLS = [
    "awk",
    "basename",
    "cat",
    "cp",
    "cut",
    "dirname",
    "env",
    "grep",
    "gzip",
    "head",
    "ls",
    "mkdir",
    "mktemp",
    "mv",
    "openssl",
    "rm",
    "sed",
    "sh",
    "sha256sum",
    "shasum",
    "sort",
    "tar",
    "tr",
    "uname",
    "wc",
]


def archive(entries):
    """A gzip tar of (name, kind, payload) entries."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, kind, payload in entries:
            info = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = payload
                tar.addfile(info)
            else:
                data = payload.encode()
                info.size = len(data)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


GOOD = archive(
    [
        ("node-v24.0.0-test", "dir", ""),
        ("node-v24.0.0-test/bin", "dir", ""),
        ("node-v24.0.0-test/bin/node", "file", "#!/bin/sh\necho v24.0.0\n"),
        ("node-v24.0.0-test/bin/npm", "symlink", "../lib/npm"),
        ("node-v24.0.0-test/lib", "dir", ""),
        ("node-v24.0.0-test/lib/npm", "file", "#!/bin/sh\n"),
    ]
)
ARCHIVE_NAME = "node-v24.0.0-test.tar.gz"


class ShellRuntime(unittest.TestCase):
    """runtime.sh run in a PATH that holds only the tools it needs, plus chosen shims."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.home = self.tmp / "home"
        self.tools = self.tmp / "tools"
        self.shims = self.tmp / "shims"
        self.tools.mkdir()
        self.shims.mkdir()
        for name in TOOLS:
            found = shutil.which(name)
            if found:
                (self.tools / name).symlink_to(found)

    def shim(self, name, body):
        path = self.shims / name
        path.write_text(f"#!/bin/sh\n{body}\n")
        path.chmod(0o755)

    def python(self, version="3.13.1"):
        modern = tuple(int(n) for n in version.split(".")[:2]) >= (3, 10)
        status = 0 if modern else 1
        self.shim("python3", f'case "$*" in *sys.exit*) exit {status};; esac\necho {version}')

    def node(self, version="v24.1.0", npm=True):
        self.shim("node", f"echo {version}")
        if npm:
            self.shim("npm", "echo 10.0.0")

    def run_script(self, *args, base=None, shims=True):
        env = {
            "PATH": os.pathsep.join([str(self.shims)] * shims + [str(self.tools)]),
            "HOME": str(self.tmp),
            "SPECWRIGHT_HOME": str(self.home),
        }
        if base is not None:
            env["SPECWRIGHT_RUNTIME_TEST_BASE"] = base
        done = subprocess.run(
            [shutil.which("sh"), str(SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
            check=False,
        )
        return done.returncode, done.stdout, done.stderr

    def mirror(self, data, name=ARCHIVE_NAME, digest=None):
        """A file:// folder holding an archive and the pins that name it for every platform."""
        folder = self.tmp / "mirror"
        folder.mkdir(exist_ok=True)
        (folder / name).write_bytes(data)
        digest = digest or hashlib.sha256(data).hexdigest()
        rows = ["base\thttps://nodejs.org/dist/v24.0.0"]
        rows += [f"{key}\t{name}\t{digest}" for key in sorted(PLATFORMS)]
        (folder / "runtime-pins.tsv").write_text("\n".join(rows) + "\n")
        return f"file://{folder}"

    def installed(self):
        runtime_dir = self.home / "runtime"
        return sorted(p.name for p in runtime_dir.glob("*")) if runtime_dir.exists() else []


class CheckTests(ShellRuntime):
    def test_everything_present_exits_zero(self):
        self.python()
        self.node()
        code, out, _ = self.run_script("check")
        self.assertEqual(code, 0, out)
        self.assertIn("python: 3.13.1 (ok; need >=3.10)", out)
        self.assertIn("node: 24.1.0 (ok; need >=24)", out)
        self.assertIn("npm: - (ok; need bundled with Node)", out)

    def test_it_reports_when_python_is_missing(self):
        """The reason this is a shell script: it must run when Python does not exist."""
        self.node()
        code, out, err = self.run_script("check")
        self.assertEqual(code, 1, err)
        self.assertIn("python: - (missing or too old; need >=3.10)", out)
        self.assertIn("node: 24.1.0 (ok", out)

    def test_an_old_python_is_too_old(self):
        self.python("3.9.6")
        self.node()
        code, out, _ = self.run_script("check")
        self.assertEqual(code, 1)
        self.assertIn("python: 3.9.6 (missing or too old", out)

    def test_an_old_node_is_too_old(self):
        self.python()
        self.node("v18.20.0")
        code, out, _ = self.run_script("check")
        self.assertEqual(code, 1)
        self.assertIn("node: 18.20.0 (missing or too old; need >=24)", out)

    def test_node_missing_and_json_shape(self):
        self.python()
        code, out, _ = self.run_script("check", "--json")
        self.assertEqual(code, 1)
        report = json.loads(out)
        self.assertTrue(report["python"]["ok"])
        self.assertEqual(report["python"]["version"], "3.13.1")
        self.assertFalse(report["node"]["ok"])
        self.assertIsNone(report["node"]["path"])
        self.assertEqual(report["node"]["need"], ">=24")

    def test_the_node_this_kit_installed_wins_over_one_on_path(self):
        self.python()
        self.node("v18.20.0")
        own = self.home / "runtime/node-v24.2.0-test/bin"
        own.mkdir(parents=True)
        (own / "node").write_text("#!/bin/sh\necho v24.2.0\n")
        (own / "node").chmod(0o755)
        (own / "npm").write_text("#!/bin/sh\n")
        code, out, _ = self.run_script("check", "--json")
        self.assertEqual(code, 0, out)
        report = json.loads(out)
        self.assertEqual(report["node"]["version"], "24.2.0")
        self.assertTrue(report["node"]["path"].startswith(str(self.home)))

    def test_help_and_usage(self):
        self.assertEqual(self.run_script("--help")[0], 0)
        self.assertEqual(self.run_script()[0], 2)
        self.assertEqual(self.run_script("frobnicate")[0], 2)


class PlanTests(ShellRuntime):
    def test_the_node_plan_names_the_download_and_changes_nothing(self):
        code, out, _ = self.run_script("plan", "node")
        self.assertEqual(code, 0)
        self.assertIn("https://nodejs.org/dist/v", out)
        self.assertIn("sha256", out)
        self.assertIn(str(self.home / "runtime"), out)
        self.assertIn("No administrator rights", out)
        self.assertFalse(self.home.exists())

    def test_the_python_plan_gives_one_command_and_changes_nothing(self):
        code, out, _ = self.run_script("plan", "python")
        self.assertEqual(code, 0)
        self.assertIn("Command:", out)
        self.assertFalse(self.home.exists())


class InstallTests(ShellRuntime):
    def test_refuses_without_the_users_approval(self):
        for tool in ("node", "python"):
            code, _, err = self.run_script("install", tool)
            self.assertEqual(code, 3, tool)
            self.assertIn("approval", err)
        self.assertFalse(self.home.exists())

    def test_installs_a_verified_archive_under_the_user_folder(self):
        code, out, err = self.run_script("install", "node", "--yes", base=self.mirror(GOOD))
        self.assertEqual(code, 0, err)
        folder = self.home / "runtime/node-v24.0.0-test"
        self.assertIn(f"installed: {folder}", out)
        self.assertTrue((folder / "bin/node").is_file())
        self.assertTrue((folder / "bin/npm").is_symlink())
        self.assertTrue((folder / "bin/node").stat().st_mode & stat.S_IXUSR)
        self.assertEqual(self.installed(), ["node-v24.0.0-test"])
        again, out, _ = self.run_script("install", "node", "--yes", base=self.mirror(b"unused"))
        self.assertEqual((again, folder.as_posix() in out), (0, True))

    def test_the_installed_node_counts_as_node_24(self):
        self.python()
        self.run_script("install", "node", "--yes", base=self.mirror(GOOD))
        code, out, _ = self.run_script("check", "--json")
        self.assertEqual(code, 0, out)
        report = json.loads(out)
        self.assertTrue(report["node"]["ok"])
        self.assertTrue(report["node"]["path"].startswith(str(self.home)))

    def test_a_checksum_mismatch_stops_before_unpacking(self):
        mirror = self.mirror(GOOD, digest="0" * 64)
        code, _, err = self.run_script("install", "node", "--yes", base=mirror)
        self.assertEqual(code, 2)
        self.assertIn("sha256", err)
        self.assertEqual(self.installed(), [])

    def test_unsafe_archives_are_rejected(self):
        for entries in (
            [("node-v24.0.0-test/../escape", "file", "x")],
            [("/abs/file", "file", "x")],
            [("node-v24.0.0-test/link", "symlink", "/etc/passwd")],
            [("node-v24.0.0-test/link", "symlink", "../../outside")],
        ):
            code, _, err = self.run_script(
                "install", "node", "--yes", base=self.mirror(archive(entries))
            )
            self.assertEqual(code, 2, entries)
            self.assertIn("unsafe", err, entries)
            self.assertEqual(self.installed(), [], entries)
            self.assertFalse((self.home / "escape").exists())

    def test_a_download_location_that_is_not_a_local_folder_is_refused(self):
        code, _, err = self.run_script("install", "node", "--yes", base="https://example.com/dist")
        self.assertEqual(code, 2)
        self.assertIn("file://", err)
        self.assertFalse(self.home.exists())

    def test_python_is_never_installed_with_sudo(self):
        self.shim("apt-get", "exit 0")
        code, out, _ = self.run_script("install", "python", "--yes")
        self.assertEqual(code, 4)
        self.assertIn("sudo apt-get install", out)
        self.assertIn("yourself", out)


class PinTests(unittest.TestCase):
    def rows(self):
        lines = [x for x in PINS.read_text().splitlines() if x and not x.startswith("#")]
        return [line.split("\t") for line in lines]

    def test_every_platform_has_a_pin_that_names_the_pinned_version(self):
        rows = self.rows()
        base = next(r[1] for r in rows if r[0] == "base")
        version = base.rsplit("/v", 1)[1]
        pins = {r[0]: r for r in rows if r[0] != "base"}
        self.assertEqual(set(pins), PLATFORMS)
        for _, name, digest in pins.values():
            self.assertEqual(len(digest), 64)
            self.assertIn(f"node-v{version}-", name)
        self.assertTrue(version.startswith("24."))
        self.assertTrue(base.startswith("https://nodejs.org/dist/"))

    def test_the_powershell_script_reads_the_same_pins_file(self):
        text = (ROOT / "skills/_shared/scripts/runtime.ps1").read_text()
        self.assertIn("runtime-pins.tsv", text)
        self.assertIn("win-x64", text)


class HookTests(ShellRuntime):
    def command(self):
        data = json.loads(HOOKS.read_text())
        return data["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    def run_hook(self):
        env = {
            "PATH": os.pathsep.join([str(self.shims), str(self.tools)]),
            "HOME": str(self.tmp),
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
        }
        done = subprocess.run(
            self.command(),
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=self.tmp,
            timeout=60,
            check=False,
        )
        return done.returncode, done.stdout, done.stderr

    def test_without_python_the_session_start_hook_says_so_and_does_not_fail(self):
        code, out, err = self.run_hook()
        self.assertEqual(code, 0, err)
        self.assertIn("Python 3.10 or newer was not found", out)
        self.assertNotIn("not found:", err)

    def test_an_old_python_gets_the_same_message(self):
        self.python("3.9.6")
        code, out, _ = self.run_hook()
        self.assertEqual(code, 0)
        self.assertIn("Python 3.10 or newer was not found", out)


class PythonSideTests(unittest.TestCase):
    def test_python_is_reported(self):
        status = runtime.check()
        self.assertTrue(status["python"]["ok"])

    def test_the_node_folder_the_shell_installer_made_is_found(self):
        with tempfile.TemporaryDirectory() as temp:
            node = Path(temp) / "runtime/node-v24.0.0-test/bin"
            node.mkdir(parents=True)
            (node / "node").write_text("#!/bin/sh\necho v24.0.0\n")
            (node / "node").chmod(0o755)
            (node / "npm").write_text("#!/bin/sh\n")
            with mock.patch.dict(os.environ, {"SPECWRIGHT_HOME": temp}):
                status = runtime.check()
                self.assertTrue(status["node"]["ok"])
                self.assertTrue(status["npm"]["ok"])
                self.assertEqual(runtime.env_with_node()["PATH"].split(os.pathsep)[0], str(node))


class StartTests(unittest.TestCase):
    def test_the_session_hook_mentions_a_missing_node_only(self):
        spec = importlib.util.spec_from_file_location("sw_start_for_runtime", START)
        start = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(start)
        base = {
            "kit_version": "x",
            "layout": "docs",
            "spec_root": "/r",
            "mode": "flat",
            "scopes_state": [],
        }
        missing = "\n".join(start.hook_lines({**base, "runtime": {"node": False}}))
        present = "\n".join(start.hook_lines({**base, "runtime": {"node": True}}))
        self.assertIn("Node 24 is not installed", missing)
        self.assertNotIn("Node 24", present)


if __name__ == "__main__":
    unittest.main()
