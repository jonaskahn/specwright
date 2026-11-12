"""An existing baseline goes through the whole kit: import, names, conflicts, answers, logs.

The fixture holds a legacy register, a remote page tree larger than one result page, an index-only
parent page, sample personal data inside policy text, two pages that disagree, a legacy item
without a source page and a source page without a legacy item. Each test checks one of the
acceptance criteria of the findability and baseline work against the state built once in setUpClass.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kitlib import (
    cite,
    frontmatter,
    graph,
    graph_query,
    hashing,
    scanlog,
    workspace,
    writelog,
)

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
FIXTURE = ROOT / "fixtures/baseline"
A = "/wiki/api/v2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(module)
    return module


wiki_pull = load("acceptance_wiki_pull", SKILLS / "sw-ingest/scripts/wiki_pull.py")
to_md = load("acceptance_to_md", SKILLS / "sw-ingest/scripts/to_md.py")


class Fake:
    """The page tree of the fixture, with the children of the home page split over two cursors."""

    def __init__(self, tree):
        pages = tree["pages"]
        self.routes = {}
        for pid, page in pages.items():
            self.routes[f"{A}/pages/{pid}?body-format=storage"] = {
                "id": pid,
                "title": page["title"],
                "parentId": page["parent"] or None,
                "version": {"number": page["version"]},
                "body": {"storage": {"value": page["body"]}},
                "_links": {"base": "https://wiki.example.test/wiki", "webui": f"/pages/{pid}"},
            }
            for leaf in ("labels", "attachments"):
                self.routes[f"{A}/pages/{pid}/{leaf}?limit=100"] = {"results": []}
            kids = [
                {"id": k, "title": p["title"], "childPosition": p.get("position", 0)}
                for k, p in pages.items()
                if p["parent"] == pid
            ]
            if pid == "100":
                self.routes[f"{A}/pages/100/children?limit=100"] = {
                    "results": kids[:2],
                    "_links": {"next": f"{A}/pages/100/children?cursor=p2&limit=100"},
                }
                self.routes[f"{A}/pages/100/children?cursor=p2&limit=100"] = {"results": kids[2:]}
            else:
                self.routes[f"{A}/pages/{pid}/children?limit=100"] = {"results": kids}

    def get(self, path):
        if path not in self.routes:
            raise AssertionError(f"unexpected request {path}")
        return self.routes[path]


def run(script, *args, cwd, flag=True):
    return subprocess.run(
        [sys.executable, str(script), *args, *(["--cwd", str(cwd)] if flag else [])],
        capture_output=True,
        text=True,
        timeout=120,
    )


class BaselineAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.base = cls.root
        tree = json.loads((FIXTURE / "tree.json").read_text())
        workspace.init(
            cls.root,
            "flat",
            "REF",
            "Refunds",
            approvers=[{"role": "PO", "name": "Lan", "account_id": "712020:aa11"}],
        )
        workspace.add_source(
            cls.root, "REF", "wiki", "confluence", "REFUNDS/100", "2026-11-01", 5, r"LEG-\d{3}"
        )
        # 1. pull the tree and import it; one page holds sample personal data and is refused
        code = wiki_pull.main(
            [
                "--batch-id",
                "pull1",
                "--root-page",
                "100",
                "--space",
                "REFUNDS",
                "--cwd",
                str(cls.root),
            ],
            Fake(tree),
        )
        assert code == 0
        cls.pull = cls.base / "_meta/work/pull-pull1"
        cls.first = run(
            SKILLS / "sw-ingest/scripts/bulk_import.py",
            "--batch-id",
            "b1",
            "--list-file",
            str(cls.pull / "list.tsv"),
            "--source-id",
            "wiki",
            cwd=cls.root,
        )
        # 2. a named person reviews the sample value as a documented example; re-import that page
        page = cls.pull / "101.html"
        text = to_md.clean(to_md.convert(page, page.read_bytes(), "en")[0], [])
        line = next(n for n, ln in enumerate(text.splitlines(), 1) if "owner@example.test" in ln)
        scanlog.append(
            cls.base / "_meta/scan-decisions.tsv",
            {
                "source_hash": hashing.bytes_hash(page.read_bytes()),
                "line": line,
                "type": "email",
                "decision": "example",
                "by": "PO | Lan",
                "ref": "https://example.test/review/example-email",
                "date": "2026-11-12",
            },
        )
        rows = (cls.pull / "list.tsv").read_text().splitlines()
        (cls.pull / "retry.tsv").write_text(
            "\n".join([rows[0], *[r for r in rows[1:] if "\t101\t" in r]]) + "\n"
        )
        cls.second = run(
            SKILLS / "sw-ingest/scripts/bulk_import.py",
            "--batch-id",
            "b2",
            "--list-file",
            str(cls.pull / "retry.tsv"),
            "--expected",
            "1",
            cwd=cls.root,
        )
        # 3. the legacy register, one reserved feature per legacy item, the graph
        shell = SKILLS / "sw-shape/scripts/baseline.py"
        run(
            shell,
            "import-register",
            str(FIXTURE / "register.csv"),
            "--source-id",
            "wiki",
            cwd=cls.root,
        )
        for group in ("Refunds", "Payments", "Accounts"):
            run(shell, "reserve", "--group", group, cwd=cls.root)
        graph.build(cls.root, "REF")
        cls.snap = {
            fm["remote_id"]: fm["id"]
            for fm in (
                frontmatter.parse(p.read_text()).fm
                for p in (cls.base / "00-inbox").glob("SRC-*.md")
            )
        }
        # 4. candidates: one worker reads every page; two claims disagree
        run(SKILLS / "sw-ingest/scripts/candidates.py", "assign", cwd=cls.root)
        cls.fill_candidates()
        cls.conflict = run(SKILLS / "sw-ingest/scripts/candidates.py", "conflicts", cwd=cls.root)
        record = SKILLS / "_shared/scripts/record.py"
        cls.asked = run(
            record,
            "q",
            "new",
            "--title",
            "Which refund window applies",
            "--affects",
            "FEAT-001",
            "--affects",
            "FEAT-002",
            "--owner",
            "PO",
            "--raised-from",
            "CAND-001.1",
            "--raised-from",
            "CAND-001.2",
            "--status",
            "open",
            "--format",
            "json",
            cwd=cls.root,
        )
        graph.build(cls.root, "REF")
        cls.board_open = {r["id"]: r for r in graph_query.board(graph_query.Store(cls.root, "REF"))}
        # 5. specify FEAT-002, answer in a meeting, track the wording change
        story = run(
            SKILLS / "sw-spec/scripts/new_story.py",
            "--reserved",
            "FEAT-002",
            "--scope-root",
            str(cls.base),
            "--scope",
            "REF",
            cwd=cls.root,
            flag=False,
        )
        assert story.returncode == 0, story.stderr
        path = cls.base / "02-drafts/FEAT-002.story.md"
        path.write_text(
            path.read_text().replace("## Goal\n", "## Goal\nRefunds close after 14 days.\n", 1)
        )
        cls.answered = run(
            record,
            "q",
            "answer",
            "Q-001",
            "--answer",
            "Use the 30 day window.",
            "--decided-by-role",
            "PO",
            "--decided-by-name",
            "Lan",
            "--evidence-kind",
            "meeting",
            "--evidence-ref",
            "minutes-2026-11-12",
            "--amend",
            "FEAT-002||Refunds close after 14 days||Refunds close after 30 days",
            "--format",
            "json",
            cwd=cls.root,
        )
        cls.lint_pending = cls.lint()
        path.write_text(path.read_text().replace("14 days", "30 days", 1))
        cls.applied = run(record, "amend", "apply", "AMD-001", cwd=cls.root)
        cls.lint_done = cls.lint()
        graph.build(cls.root, "REF")

    @classmethod
    def fill_candidates(cls):
        from kitlib import candidates, tables

        worker = next(candidates.folder(cls.base).glob("CAND-001--*.md"))
        sources = cite.Sources(cls.base)

        def at(remote, needle):
            ident = cls.snap[remote]
            lines = sources.lines(ident)
            number = next(n for n, ln in enumerate(lines, 1) if needle in ln)
            return cite.stamp(sources, cite.parse_one(f"{ident}:L{number}"))

        rows = [
            ("rule", "Refund window", "Refunds close after 14 days", at("101", "14 days")),
            ("rule", "refund window", "Refunds close after 30 days", at("102", "30 days")),
            (
                "rule",
                "Payout method",
                "A payout returns to the original payment method",
                at("103", "payout"),
            ),
        ]
        parsed = frontmatter.parse(worker.read_text())
        table = tables.Table(list(candidates.HEADER))
        for n, (kind, topic, claim, citation) in enumerate(rows, 1):
            table.rows.append([str(n), kind, topic, claim, citation, "raw", tables.EMPTY])
        fm = dict(parsed.fm)
        fm["count"] = len(rows)
        head = parsed.body.split("## Candidates")[0]
        worker.write_text(frontmatter.render(fm, head + "## Candidates\n\n" + table.render()))

    @classmethod
    def lint(cls):
        result = subprocess.run(
            [
                sys.executable,
                str(SKILLS / "_shared/scripts/sw_lint.py"),
                "--root",
                str(cls.root),
                "--gate",
                "review",
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return json.loads(result.stdout)["findings"]

    # ---- 1. import reports counts and every snapshot has provenance

    def test_1_import_reports_expected_and_received_counts_with_complete_provenance(self):
        self.assertEqual(self.first.returncode, 3)  # one page needed a human decision
        one = json.loads((self.base / "00-inbox/imports/b1/manifest.json").read_text())
        self.assertEqual((one["expected_count"], one["received_count"]), (5, 5))
        self.assertEqual(one["counts"], {"created": 4, "refused": 1})
        self.assertEqual(self.second.returncode, 0, self.second.stderr)
        two = json.loads((self.base / "00-inbox/imports/b2/manifest.json").read_text())
        self.assertEqual((two["counts"], two["counts_match"]), ({"created": 1}, True))
        self.assertEqual(set(self.snap), {"100", "101", "102", "103", "104"})
        for path in (self.base / "00-inbox").glob("SRC-*.md"):
            fm = frontmatter.parse(path.read_text()).fm
            for field in (
                "title",
                "aliases",
                "source",
                "source_version",
                "remote_id",
                "remote_url",
                "fetched_at",
                "sha256",
                "converter",
            ):
                self.assertTrue(fm.get(field), f"{path.name} lacks {field}")
        home = frontmatter.parse(
            next((self.base / "00-inbox").glob(f"{self.snap['100']}--*.md")).read_text()
        ).fm
        self.assertEqual(home["content_class"], "index-only")

    # ---- 2. every legacy item resolves by any of its names

    def test_2_every_legacy_item_resolves_by_any_name_to_one_record_and_its_crosswalk_row(self):
        store = graph_query.Store(self.root, "REF")
        by_name = {
            "LEG-100": "REF:FEAT-001",
            "LEG-101": "REF:FEAT-002",
            "LEG-200": "REF:FEAT-003",
            "LEG-201": "REF:FEAT-004",
            "LEG-300": "REF:FEAT-005",
            "Request a refund": "REF:FEAT-001",
            "Issue a payout": "REF:FEAT-003",
            "101": f"REF:{self.snap['101']}",
            "https://wiki.example.test/wiki/pages/102": f"REF:{self.snap['102']}",
            "Refund payout": f"REF:{self.snap['102']}",
        }
        for name, key in by_name.items():
            self.assertEqual(store.resolve(name, fuzzy=True), key, name)
        shown = "\n".join(graph_query.show(store, "REF:FEAT-001"))
        self.assertIn("crosswalk: LEG-100 -> REF:FEAT-001", shown)
        lines = (self.base / "_meta/CROSSWALK.tsv").read_text().splitlines()
        head = lines[1][2:].split("\t")
        rows = [dict(zip(head, ln.split("\t"), strict=False)) for ln in lines[2:]]
        match = {r["legacy_id"] or "(none)": r["match"] for r in rows}
        self.assertEqual(match["LEG-100"], "matched")
        self.assertEqual(match["LEG-300"], "no-source")  # a legacy item without a source page
        self.assertEqual(match["(none)"], "no-register")  # a source page without a legacy item

    # ---- 3. every conflict is a recorded question shown on every affected feature

    def test_3_the_conflict_is_a_recorded_question_blocking_every_affected_feature(self):
        self.assertIn("topic Refund window", self.conflict.stdout)
        self.assertIn("1 conflict(s)", self.conflict.stdout)
        self.assertEqual(self.asked.returncode, 0, self.asked.stderr)
        for feat in ("REF:FEAT-001", "REF:FEAT-002"):
            self.assertEqual(self.board_open[feat]["blocked_by_q"], ["REF:Q-001"], feat)
        self.assertEqual(self.board_open["REF:FEAT-003"]["blocked_by_q"], [])

    # ---- 4. every citation verifies

    def test_4_every_citation_in_every_record_verifies(self):
        result = run(SKILLS / "_shared/scripts/cite.py", "verify", cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        question = next((self.base / "records").glob("Q-001--*.md")).read_text()
        self.assertEqual(len(cite.find(question)), 4)  # two stamped fields and two quoted blocks

    # ---- 5. an answer is a decision and a tracked amendment

    def test_5_answering_records_a_decision_and_a_tracked_amendment(self):
        self.assertEqual(self.answered.returncode, 0, self.answered.stderr)
        self.assertEqual(json.loads(self.answered.stdout)["made"], ["DEC-001", "AMD-001"])
        dec = frontmatter.parse(next((self.base / "records").glob("DEC-001--*.md")).read_text()).fm
        self.assertEqual(dec["decided_by"]["name"], "Lan")
        self.assertEqual(
            (dec["evidence_kind"], dec["evidence_ref"]), ("meeting", "minutes-2026-11-12")
        )
        self.assertIn("L-062", {f["rule"] for f in self.lint_pending})
        self.assertEqual(self.applied.returncode, 0, self.applied.stderr)
        self.assertNotIn("L-062", {f["rule"] for f in self.lint_done})

    # ---- 6. the write log accounts for every change; no stray folders

    def test_6_the_write_log_accounts_for_every_record_and_no_folder_is_stray(self):
        log = self.base / "_meta/write-log.md"
        self.assertEqual(writelog.unfinished(log), [])
        self.assertEqual(writelog.drift(log), [])
        logged = {
            item[5:].rsplit("@", 1)[0]
            for e in writelog.read(log)
            if e.kind == "RESULT"
            for item in e.fields
            if item.startswith("file=")
        }
        for path in sorted((self.base / "records").glob("*.md")):
            self.assertIn(f"records/{path.name}", logged)
        for path in sorted((self.base / "00-inbox").glob("SRC-*.md")):
            self.assertIn(f"00-inbox/{path.name}", logged)
        self.assertEqual(workspace.stray_folders(self.base), [])

    # ---- 7. a new session can work from READ-FIRST and queries alone

    def test_7_read_first_and_queries_name_each_items_state_and_next_action(self):
        text = (self.base / "_meta/READ-FIRST.md").read_text()
        for needle in (
            "project.yaml",
            "AGENTS.md",
            "INDEX.md",
            "CROSSWALK.tsv",
            "graph.py board",
            "do not open folders",
        ):
            self.assertIn(needle, text)
        store = graph_query.Store(self.root, "REF")
        rows = {r["id"]: r for r in graph_query.board(store)}
        self.assertEqual(set(rows), {f"REF:FEAT-00{n}" for n in range(1, 6)})
        for row in rows.values():
            self.assertTrue(row["station"] and row["condition"] and row["available"])
        self.assertEqual(rows["REF:FEAT-002"]["station"], "spec")
        self.assertEqual(rows["REF:FEAT-002"]["blocked_by_q"], [])  # answered, so no longer blocked
        pack = subprocess.run(
            [sys.executable, str(SKILLS / "sw-start/scripts/start.py"), "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        item = json.loads(pack.stdout)["scopes_state"][0]
        self.assertTrue(item["action"])
