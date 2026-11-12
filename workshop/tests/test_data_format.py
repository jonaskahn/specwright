import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import dataformat, gitignore, graph, graph_query, workspace

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "skills/_shared/scripts/data.py"
FIXTURE = ROOT / "workshop/fixtures/refund/after-spec"
OWNER_OF = {name: kind.owner for name, kind in dataformat.KINDS.items()}


def git(path, *args):
    return subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True, check=True
    ).stdout


class DataTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "docs"
        shutil.copytree(FIXTURE, self.root)
        graph.build(self.root, "REF")

    def export_all(self):
        for kind, owner in OWNER_OF.items():
            dataformat.write_kind(self.root, kind, owner, "REF")

    def cli(self, *args):
        done = subprocess.run(
            [sys.executable, str(DATA), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return done.returncode, done.stdout, done.stderr

    def test_every_kind_is_written_valid_and_indexed(self):
        self.export_all()
        folder = self.root / "_meta/data"
        index = json.loads((folder / "index.json").read_text())
        self.assertEqual(sorted(index["files"]), sorted(k.file for k in dataformat.KINDS.values()))
        for kind in dataformat.KINDS:
            doc = json.loads((folder / f"{kind}.json").read_text())
            self.assertEqual(dataformat.validate(doc, kind), [], kind)
        self.assertEqual(dataformat.check(self.root, "REF"), [])

    def test_rows_carry_qualified_keys_and_null_placeholders(self):
        self.export_all()
        folder = self.root / "_meta/data"
        features = json.loads((folder / "features.json").read_text())["rows"]
        self.assertEqual([r["id"] for r in features], ["REF:FEAT-001", "REF:FEAT-002"])
        first = features[0]
        self.assertIsNone(first["jira"])
        self.assertEqual((first["acCount"], first["state"]), (2, "in-review"))
        self.assertEqual(
            [row["illustration"] for row in features],
            ["needs illustration", "no illustration"],
        )
        self.assertEqual(first["openQuestions"], ["REF:Q-001"])
        nodes = json.loads((folder / "graph.json").read_text())["nodes"]
        self.assertTrue(all(n["key"].startswith("REF:") for n in nodes))

    def test_output_is_byte_deterministic(self):
        self.export_all()
        folder = self.root / "_meta/data"
        first = {p.name: p.read_bytes() for p in folder.glob("*.json")}
        self.export_all()
        self.assertEqual(first, {p.name: p.read_bytes() for p in folder.glob("*.json")})

    def test_a_skill_cannot_write_another_skills_kind(self):
        with self.assertRaises(dataformat.DataError):
            dataformat.write_kind(self.root, "tasks", "sw-spec", "REF")
        code, _, err = self.cli("export", "tasks", "--as", "sw-ingest")
        self.assertEqual(code, 2)
        self.assertIn("owned by sw-plan", err)

    def test_export_all_writes_only_what_the_skill_may_write(self):
        code, out, _ = self.cli("export", "all", "--as", "sw-plan")
        self.assertEqual(code, 0, out)
        names = {p.name for p in (self.root / "_meta/data").glob("*.json")}
        self.assertEqual(names, {"index.json", "graph.json", "tasks.json", "rtm.json"})

    def test_validation_rejects_bad_rows(self):
        self.export_all()
        doc = json.loads((self.root / "_meta/data/graph.json").read_text())
        doc["edges"][0]["rel"] = "invented"
        doc["nodes"][0]["extra"] = 1
        doc["nodes"][1]["title"] = None
        errors = "\n".join(dataformat.validate(doc, "graph"))
        self.assertIn("edges[0].rel", errors)
        self.assertIn("nodes[0].extra: unknown field", errors)
        self.assertIn("nodes[1].title: must not be null", errors)

    def test_check_names_the_owner_of_a_missing_or_stale_file(self):
        self.export_all()
        (self.root / "_meta/data/tasks.json").unlink()
        (self.root / "02-drafts/FEAT-002.story.md").write_text(
            (self.root / "02-drafts/FEAT-002.story.md").read_text() + "\nmore\n"
        )
        found = {f["kind"]: f for f in dataformat.check(self.root, "REF")}
        self.assertEqual(found["tasks"]["status"], "missing")
        self.assertEqual(found["tasks"]["owner"], "sw-plan")
        self.assertEqual(found["records"]["status"], "stale")
        code, out, _ = self.cli("check")
        self.assertEqual(code, 4)
        self.assertIn("sw-plan owns it", out)

    def test_graph_export_refuses_a_stale_graph(self):
        (self.root / "02-drafts/FEAT-002.story.md").write_text(
            (self.root / "02-drafts/FEAT-002.story.md").read_text() + "\nmore\n"
        )
        with self.assertRaises(dataformat.DataError) as caught:
            dataformat.write_kind(self.root, "graph", "sw-start", "REF")
        self.assertIn("graph.py build", str(caught.exception))

    def test_graph_build_script_refreshes_graph_json(self):
        script = ROOT / "skills/_shared/scripts/graph.py"
        done = subprocess.run(
            [sys.executable, str(script), "build", "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue((self.root / "_meta/data/graph.json").is_file())

    def test_no_body_text_leaves_the_project(self):
        story = self.root / "02-drafts/FEAT-001.story.md"
        story.write_text(story.read_text() + "\nPlain secret sentence for the body.\n")
        graph.build(self.root, "REF")
        self.export_all()
        blob = "".join(p.read_text() for p in (self.root / "_meta/data").glob("*.json"))
        self.assertNotIn("Plain secret sentence", blob)


class ConsoleFolderTests(unittest.TestCase):
    """The console folder sits beside the spec folders in both layouts and is never evidence."""

    def check(self, base, root, scope):
        before = graph.check(root, scope)
        (base / "console").mkdir()
        (base / "console/index.html").write_text("<p>FEAT-009</p>")
        (base / "console/notes.md").write_text("---\nid: FEAT-009\n---\nnot evidence\n")
        graph.build(root, scope)
        self.assertEqual(graph.check(root, scope), before)
        self.assertEqual(workspace.stray_folders(base), [])
        self.assertIsNone(graph_query.Store(root, scope).node(f"{scope}:FEAT-009"))

    def test_docs_layout(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "docs"
        shutil.copytree(FIXTURE, root)
        graph.build(root, "REF")
        self.check(root, root, "REF")

    def test_embedded_layout(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / ".specwright"
        shutil.copytree(FIXTURE, root)
        scope = "REF"
        graph.build(root, scope)
        self.assertEqual(workspace.layout_of(root), "embedded")
        self.check(root, root, scope)


class GitHygieneTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        git(self.repo, "init", "-q")
        self.root = self.repo / "docs"
        shutil.copytree(FIXTURE, self.root)
        graph.build(self.root, "REF")
        for kind, owner in OWNER_OF.items():
            dataformat.write_kind(self.root, kind, owner, "REF")

    def test_generated_folders_stay_out_of_git(self):
        git(self.repo, "add", "-A")
        staged = git(self.repo, "diff", "--cached", "--name-only")
        self.assertNotIn("_meta/data", staged)
        self.assertIn("docs/_meta/graph", staged)
        self.assertEqual(git(self.repo, "status", "--porcelain", "docs/_meta/data"), "")

    def test_the_repository_gitignore_is_not_touched(self):
        self.assertFalse((self.repo / ".gitignore").exists())
        self.assertEqual((self.root / "_meta/data/.gitignore").read_text(), "*\n")

    def test_an_existing_folder_keeps_its_own_gitignore(self):
        (self.root / "_meta/data/.gitignore").unlink()
        dataformat.write_kind(self.root, "tasks", "sw-plan", "REF")
        self.assertFalse((self.root / "_meta/data/.gitignore").exists())

    def test_check_warns_and_never_runs_git_changes(self):
        (self.root / "_meta/data/.gitignore").unlink()
        git(self.repo, "add", "-f", "docs/_meta/data")
        findings = gitignore.git_findings(self.root / "_meta/data", ["index.json"])
        self.assertTrue(any("git rm -r --cached" in f for f in findings))
        self.assertIn("docs/_meta/data/index.json", git(self.repo, "ls-files"))


if __name__ == "__main__":
    unittest.main()
