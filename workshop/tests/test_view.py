import http.client
import importlib.util
import io
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from kitlib import dataformat, graph, view_build, view_extract, view_server

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/sw-view"
ZIP = SKILL / "assets/console.zip"
MANIFEST = SKILL / "assets/console.manifest.json"
VIEW = SKILL / "scripts/view.py"
FIXTURE = ROOT / "workshop/fixtures/refund/after-spec"
POSIX = sys.platform != "win32"


def make_pack(files, symlink=None):
    """A zip and manifest for ``files`` (name -> bytes), built the way console_pack builds them."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_STORED) as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
            info.external_attr = (0o120777 if name == symlink else 0o100644) << 16
            archive.writestr(info, data)
    raw = buffer.getvalue()
    hashes = {n: view_extract.sha(d) for n, d in files.items()}
    manifest = {
        "console": "9.9.9",
        "files": hashes,
        "tree": view_extract.sha(json.dumps(hashes, sort_keys=True).encode()),
        "zip": view_extract.sha(raw),
    }
    return raw, manifest


class ExtractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.dest = self.tmp / "spec" / "console"

    def pack(self, files, **kwargs):
        raw, manifest = make_pack(files, **kwargs)
        (self.tmp / "c.zip").write_bytes(raw)
        (self.tmp / "m.json").write_text(json.dumps(manifest))
        return self.tmp / "c.zip", self.tmp / "m.json"

    def extract(self, files, force=False, **kwargs):
        zip_path, manifest = self.pack(files, **kwargs)
        return view_extract.extract(zip_path, manifest, self.dest, force)

    def test_the_committed_console_unpacks_and_ignores_itself(self):
        self.assertEqual(view_extract.extract(ZIP, MANIFEST, self.dest), "extracted")
        self.assertTrue((self.dest / "package.json").is_file())
        self.assertTrue((self.dest / "contract/types.ts").is_file())
        self.assertEqual((self.dest / ".gitignore").read_text(), "*\n")
        self.assertEqual(view_extract.extract(ZIP, MANIFEST, self.dest), "current")

    def test_local_changes_are_kept_unless_forced(self):
        self.extract({"a.txt": b"one", "b.txt": b"two"})
        (self.dest / "a.txt").write_text("mine")
        (self.dest / "extra.txt").write_text("new")
        with self.assertRaises(view_extract.ExtractError) as caught:
            self.extract({"a.txt": b"one", "b.txt": b"changed"})
        self.assertIn("local changes", str(caught.exception))
        self.assertEqual((self.dest / "a.txt").read_text(), "mine")
        self.assertEqual(
            self.extract({"a.txt": b"one", "b.txt": b"changed"}, force=True), "extracted"
        )
        self.assertEqual((self.dest / "a.txt").read_text(), "one")

    def test_an_upgrade_drops_old_files_and_keeps_dependencies_and_build(self):
        self.extract({"a.txt": b"one", "old.txt": b"x"})
        (self.dest / "node_modules").mkdir()
        (self.dest / "node_modules/keep").write_text("k")
        (self.dest / "dist").mkdir()
        (self.dest / "dist/index.html").write_text("built from old source")
        self.assertEqual(self.extract({"a.txt": b"two"}), "extracted")
        self.assertFalse((self.dest / "old.txt").exists())
        self.assertTrue((self.dest / "node_modules/keep").is_file())
        self.assertFalse((self.dest / "dist").exists())

    def test_a_folder_not_made_by_sw_view_is_not_overwritten(self):
        self.dest.mkdir(parents=True)
        (self.dest / "mine.txt").write_text("x")
        with self.assertRaises(view_extract.ExtractError):
            self.extract({"a.txt": b"one"})

    def test_a_zip_that_differs_from_its_manifest_is_refused_before_writing(self):
        zip_path, manifest = self.pack({"a.txt": b"one"})
        zip_path.write_bytes(zip_path.read_bytes() + b"x")
        with self.assertRaises(view_extract.ExtractError):
            view_extract.extract(zip_path, manifest, self.dest)
        self.assertFalse(self.dest.exists())

    def test_unsafe_archives_are_refused_even_with_a_matching_manifest(self):
        cases = {
            "parent": {"../escape.txt": b"x"},
            "absolute": {"/abs.txt": b"x"},
            "backslash": {"a\\b.txt": b"x"},
            "drive": {"C:/x.txt": b"x"},
        }
        for label, files in cases.items():
            with self.subTest(label), self.assertRaises(view_extract.ExtractError):
                self.extract(files)
            self.assertFalse((self.tmp / "escape.txt").exists())

    def test_links_are_refused(self):
        with self.assertRaises(view_extract.ExtractError):
            self.extract({"a.txt": b"x", "link": b"/etc/passwd"}, symlink="link")

    def test_too_many_entries_are_refused(self):
        with (
            mock.patch.object(view_extract, "MAX_ENTRIES", 3),
            self.assertRaises(view_extract.ExtractError),
        ):
            self.extract({f"f{i}.txt": b"x" for i in range(5)})


class ServerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        tmp = Path(temp.name)
        (tmp / "dist/assets").mkdir(parents=True)
        (tmp / "dist/index.html").write_text("<html>console</html>")
        (tmp / "dist/assets/app.js").write_text("export {}")
        (tmp / "dist/assets/secret.exe").write_text("x")
        (tmp / "data").mkdir()
        (tmp / "data/index.json").write_text("{}")
        (tmp / "data/tasks.json").write_text("{}")
        (tmp / "data/passwd.json").write_text("{}")
        (tmp / "outside.txt").write_text("private")
        self.server = view_server.make_server(tmp / "dist", tmp / "data", 47100)
        self.port = self.server.server_address[1]
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, method="GET", host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request(method, path, headers={"Host": host or f"127.0.0.1:{self.port}"})
        response = conn.getresponse()
        body = response.read()
        headers = dict(response.getheaders())
        conn.close()
        return response.status, headers, body

    def test_serves_the_console_and_data_with_a_strict_policy(self):
        status, headers, body = self.get("/")
        self.assertEqual((status, body), (200, b"<html>console</html>"))
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.get("/assets/app.js")[0], 200)
        self.assertEqual(self.get("/data/index.json")[2], b"{}")

    def test_only_the_data_formats_names_are_served(self):
        self.assertEqual(self.get("/data/tasks.json")[0], 200)
        self.assertEqual(self.get("/data/passwd.json")[0], 404)
        self.assertEqual(self.get("/data/")[0], 404)

    def test_paths_outside_the_two_folders_are_refused(self):
        for path in (
            "/../outside.txt",
            "/data/../outside.txt",
            "/assets/../../outside.txt",
            "/assets/secret.exe",
            "/etc/passwd",
        ):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_only_get_and_head_are_allowed(self):
        self.assertEqual(self.get("/", "POST")[0], 405)
        self.assertEqual(self.get("/", "PUT")[0], 405)
        status, _, body = self.get("/", "HEAD")
        self.assertEqual((status, body), (200, b""))

    def test_a_foreign_host_header_is_refused(self):
        self.assertEqual(self.get("/", host="evil.example")[0], 403)

    def test_binds_to_loopback_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_takes_the_next_free_port_when_one_is_busy(self):
        other = view_server.make_server(Path("."), Path("."), self.port)
        self.addCleanup(other.server_close)
        self.assertGreater(other.server_address[1], self.port)


class BuildTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.console = Path(temp.name)
        (self.console / "package-lock.json").write_text("{}")
        patch = mock.patch.object(view_build, "npm_command", return_value="npm")
        patch.start()
        self.addCleanup(patch.stop)
        self.calls = []

    def runner(self, fail=None, dist=True):
        def run(argv, **kwargs):
            self.calls.append(argv[1:])
            self.assertFalse(kwargs.get("shell"))
            self.assertIn("timeout", kwargs)
            if argv[1:3] == ["run", "build"] and dist:
                (self.console / "dist").mkdir(exist_ok=True)
                (self.console / "dist/index.html").write_text("x")
            code = 1 if fail and argv[1] == fail else 0
            return subprocess.CompletedProcess(argv, code, "", "boom line")

        return run

    def test_installs_with_scripts_off_then_builds(self):
        done = view_build.build(self.console, self.runner())
        self.assertEqual(done, ["npm ci", "npm run build"])
        self.assertEqual(self.calls[0][0], "ci")
        self.assertIn("--ignore-scripts", self.calls[0])

    def test_skips_the_install_while_the_lockfile_is_unchanged(self):
        view_build.build(self.console, self.runner())
        self.calls.clear()
        self.assertEqual(view_build.build(self.console, self.runner()), ["npm run build"])
        (self.console / "package-lock.json").write_text('{"changed": true}')
        self.assertEqual(view_build.build(self.console, self.runner())[0], "npm ci")

    def test_a_failing_step_is_reported_with_its_output(self):
        with self.assertRaises(view_build.BuildError) as caught:
            view_build.build(self.console, self.runner(fail="ci"))
        self.assertIn("boom line", str(caught.exception))

    def test_a_build_without_output_is_an_error(self):
        with self.assertRaises(view_build.BuildError):
            view_build.build(self.console, self.runner(dist=False))


@unittest.skipUnless(POSIX, "uses shell stubs")
class CommandTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        self.docs = self.repo / "docs"
        shutil.copytree(FIXTURE, self.docs)
        graph.build(self.docs, "REF")
        for kind, spec in dataformat.KINDS.items():
            dataformat.write_kind(self.docs, kind, spec.owner, "REF")
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.home = self.tmp / "home"

    def stub(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body)
        path.chmod(path.stat().st_mode | stat.S_IEXEC)

    def node_present(self):
        self.stub("node", 'echo "v24.1.0"\n')
        self.stub(
            "npm",
            'case "$1" in\n'
            "  ci) mkdir -p node_modules ;;\n"
            '  run) mkdir -p dist && echo "<html></html>" > dist/index.html ;;\n'
            "esac\n",
        )

    def view(self, *args, path=None):
        env = {
            "PATH": path if path is not None else f"{self.bin}:/usr/bin:/bin",
            "SPECWRIGHT_HOME": str(self.home),
            "HOME": str(self.tmp),
        }
        return subprocess.run(
            [sys.executable, str(VIEW), *args, "--cwd", str(self.docs)],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )

    @unittest.skipIf(
        shutil.which("node", path="/usr/bin:/bin"), "this machine has Node in /usr/bin"
    )
    def test_without_node_it_shows_the_plan_and_changes_nothing(self):
        done = self.view("prepare", path="/usr/bin:/bin")
        self.assertEqual(done.returncode, 3, done.stderr)
        self.assertIn("runtime.sh plan node", done.stderr)
        self.assertIn("install node --yes", done.stderr)
        self.assertFalse((self.docs / "console").exists())
        self.assertFalse(self.home.exists())

    def test_prepare_unpacks_builds_and_leaves_git_clean(self):
        self.node_present()
        done = self.view("prepare", "--format", "json", "--copy-data")
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual(report["steps"], ["npm ci", "npm run build"])
        self.assertIn("127.0.0.1", report["commands"]["url"])
        self.assertEqual(report["git_added"], [])
        console = self.docs / "console"
        self.assertTrue((console / "dist/index.html").is_file())
        self.assertTrue((console / "dist/data/index.json").is_file())
        status = subprocess.run(
            ["git", "-C", str(self.repo), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True,
            text=True,
        ).stdout
        self.assertNotIn("console/", status)
        self.assertNotIn("_meta/data", status)

    def test_prepare_never_writes_data_files(self):
        self.node_present()
        before = {p: p.read_bytes() for p in (self.docs / "_meta/data").glob("*")}
        self.assertEqual(self.view("prepare").returncode, 0)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.docs / "_meta/data").glob("*")})

    def test_a_second_prepare_reports_the_console_current(self):
        self.node_present()
        self.view("prepare")
        done = self.view("prepare", "--format", "json")
        self.assertEqual(json.loads(done.stdout)["console"], "current")

    def test_doctor_names_the_owner_of_a_missing_data_file(self):
        self.node_present()
        (self.docs / "_meta/data/tasks.json").unlink()
        done = self.view("doctor", "--format", "json")
        self.assertEqual(done.returncode, 4, done.stderr)
        self.assertTrue(any("sw-plan owns it" in line for line in json.loads(done.stdout)["data"]))

    def test_doctor_flags_a_tracked_generated_folder(self):
        self.node_present()
        (self.docs / "_meta/data/.gitignore").unlink()
        subprocess.run(["git", "-C", str(self.repo), "add", "-f", "docs/_meta/data"], check=True)
        done = self.view("doctor", "--format", "json")
        self.assertTrue(
            any("git rm -r --cached" in line for line in json.loads(done.stdout)["git"])
        )

    def test_serve_refuses_an_unbuilt_console(self):
        self.node_present()
        done = self.view("serve")
        self.assertEqual(done.returncode, 2)
        self.assertIn("prepare", done.stderr)


class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "console_pack", ROOT / "workshop/tools/console_pack.py"
        )
        cls.pack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pack)

    def test_the_committed_zip_matches_the_current_source(self):
        self.assertEqual(self.pack.check(), [], "run: python3 workshop/tools/console_pack.py")

    def test_the_zip_is_byte_deterministic(self):
        files = self.pack.tree()
        self.assertEqual(
            self.pack.build_zip(files), self.pack.build_zip(dict(reversed(files.items())))
        )

    def test_build_output_and_dependencies_never_ship(self):
        names = set(self.pack.tree())
        self.assertFalse(any(n.startswith(("node_modules/", "dist/")) for n in names))
        self.assertIn("contract/types.ts", names)
        self.assertIn("package-lock.json", names)

    def test_a_changed_source_file_makes_the_zip_stale(self):
        files = self.pack.tree()
        files["src/main.ts"] = files["src/main.ts"] + b"\n//"
        archive = self.pack.build_zip(files)
        manifest = self.pack.manifest_for(files, archive)
        self.assertNotEqual(manifest["tree"], json.loads(MANIFEST.read_text())["tree"])


if __name__ == "__main__":
    unittest.main()
