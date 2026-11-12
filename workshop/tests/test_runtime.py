import hashlib
import importlib.util
import io
import os
import stat
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kitlib import runtime, runtime_pins

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "skills/_shared/scripts/runtime.py"
START = ROOT / "skills/sw-start/scripts/start.py"


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


class InstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        env = mock.patch.dict(os.environ, {"SPECWRIGHT_HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        self.key = runtime.platform_key()
        self.pin(GOOD)

    def pin(self, data, name="node-v24.0.0-test.tar.gz"):
        pins = dict(runtime_pins.NODE_PINS)
        pins[self.key] = (name, hashlib.sha256(data).hexdigest())
        patch = mock.patch.object(runtime_pins, "NODE_PINS", pins)
        patch.start()
        self.addCleanup(patch.stop)

    def test_refuses_without_the_users_approval(self):
        with self.assertRaises(runtime.RuntimeFault) as caught:
            runtime.install_node(yes=False, fetch=lambda url: GOOD)
        self.assertIn("approval", str(caught.exception))
        self.assertFalse((self.home / "runtime").exists())

    def test_installs_a_verified_archive_under_the_user_folder(self):
        folder = runtime.install_node(yes=True, fetch=lambda url: GOOD)
        self.assertEqual(folder, self.home / "runtime" / "node-v24.0.0-test")
        self.assertTrue((folder / "bin/node").is_file())
        self.assertTrue((folder / "bin/npm").is_symlink())
        self.assertTrue((folder / "bin/node").stat().st_mode & stat.S_IXUSR)
        self.assertEqual(runtime.install_node(yes=True, fetch=lambda u: b"unused"), folder)

    def test_the_installed_node_is_found_and_counts_as_node_24(self):
        runtime.install_node(yes=True, fetch=lambda url: GOOD)
        status = runtime.check()
        self.assertTrue(status["node"]["ok"])
        self.assertTrue(str(status["node"]["path"]).startswith(str(self.home)))

    def test_a_checksum_mismatch_stops_before_unpacking(self):
        with self.assertRaises(runtime.RuntimeFault) as caught:
            runtime.install_node(yes=True, fetch=lambda url: GOOD + b"x")
        self.assertIn("sha256", str(caught.exception))
        self.assertEqual(list((self.home / "runtime").glob("node-v*")), [])

    def test_unsafe_archives_are_rejected(self):
        for entries in (
            [("node-v24.0.0-test/../escape", "file", "x")],
            [("/abs/file", "file", "x")],
            [("node-v24.0.0-test/link", "symlink", "/etc/passwd")],
            [("node-v24.0.0-test/link", "symlink", "../../outside")],
        ):
            data = archive(entries)
            self.pin(data)
            with self.assertRaises(runtime.RuntimeFault, msg=entries):
                runtime.install_node(yes=True, fetch=lambda url, d=data: d)
            self.assertFalse((self.home / "escape").exists())

    def test_only_the_pinned_location_is_downloaded(self):
        with self.assertRaises(runtime.RuntimeFault):
            runtime._download("https://example.com/node.tar.gz", lambda url: GOOD)

    def test_the_plan_names_the_download_and_changes_nothing(self):
        text = "\n".join(runtime.plan_node())
        self.assertIn("sha256", text)
        self.assertIn(str(self.home / "runtime"), text)
        self.assertFalse((self.home / "runtime").exists())


class CheckTests(unittest.TestCase):
    def test_python_is_reported(self):
        status = runtime.check()
        self.assertTrue(status["python"]["ok"])
        self.assertEqual(status["python"]["version"].split(".")[0], str(sys.version_info[0]))

    def test_every_platform_has_a_pin(self):
        self.assertEqual(
            set(runtime_pins.NODE_PINS),
            {"darwin-arm64", "darwin-x64", "linux-arm64", "linux-x64", "win-x64"},
        )
        for name, digest in runtime_pins.NODE_PINS.values():
            self.assertEqual(len(digest), 64)
            self.assertIn(runtime_pins.NODE_VERSION, name)


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
