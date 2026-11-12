"""The wiki reader pages by cursor, stays read-only and on its origin, and flags a partial pull."""

import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from kitlib import wiki_rest
from tests.test_workflow import WorkflowTestCase

SCRIPTS = Path(__file__).resolve().parents[2] / "skills/sw-ingest/scripts"
spec = importlib.util.spec_from_file_location("wiki_pull_under_test", SCRIPTS / "wiki_pull.py")
wiki_pull = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wiki_pull)
A = "/wiki/api/v2"


def page(pid, title, parent=None, version=1, body="<p>text</p>"):
    return {
        "id": pid,
        "title": title,
        "parentId": parent,
        "version": {"number": version},
        "body": {"storage": {"value": body}},
        "_links": {"base": "https://w.example.test/wiki", "webui": f"/spaces/S/pages/{pid}"},
    }


def tree(extra=None):
    """Home(100) -> Rules(101) -> Details(103); Home -> Payout(102); children paged in two calls."""
    routes = {
        f"{A}/pages/100?body-format=storage": page("100", "Home"),
        f"{A}/pages/101?body-format=storage": page("101", "Rules", "100", 3, "<p>Rules body</p>"),
        f"{A}/pages/102?body-format=storage": page("102", "Payout", "100"),
        f"{A}/pages/103?body-format=storage": page("103", "Details", "101"),
        f"{A}/pages/100/children?limit=100": {
            "results": [{"id": "102", "title": "Payout", "childPosition": 2}],
            "_links": {"next": f"{A}/pages/100/children?cursor=c2&limit=100"},
        },
        f"{A}/pages/100/children?cursor=c2&limit=100": {
            "results": [{"id": "101", "title": "Rules", "childPosition": 1}],
            "_links": {},
        },
        f"{A}/pages/101/children?limit=100": {"results": [{"id": "103", "title": "Details"}]},
        f"{A}/pages/102/children?limit=100": {"results": []},
        f"{A}/pages/103/children?limit=100": {"results": []},
    }
    for pid in ("100", "101", "102", "103"):
        routes[f"{A}/pages/{pid}/labels?limit=100"] = {
            "results": [{"name": "policy"}, {"name": "refund"}]
        }
        routes[f"{A}/pages/{pid}/attachments?limit=100"] = {
            "results": [
                {"id": "a1", "title": "rules.pdf", "fileSize": 12, "mediaType": "application/pdf"}
            ]
        }
        routes[f"{A}/pages/{pid}/footer-comments?body-format=storage&limit=100"] = {
            "results": [{"id": "9", "body": {"storage": {"value": "<p>ask legal</p>"}}}]
        }
        routes[f"{A}/pages/{pid}/inline-comments?body-format=storage&limit=100"] = {"results": []}
    routes.update(extra or {})
    return routes


class Fake:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, path):
        self.calls.append(path)
        if path not in self.routes:
            raise wiki_rest.WikiError("wiki HTTP 404")
        return self.routes[path]


class PullTests(unittest.TestCase):
    def pull(self, routes=None, **kw):
        fake = Fake(routes or tree())
        values = {"max_pages": 50, "max_depth": 3}
        values.update(kw)
        return fake, wiki_rest.Client(fake).pull_tree("100", **values)

    def test_the_whole_tree_is_read_parents_first_in_a_stable_order(self):
        _, result = self.pull()
        self.assertTrue(result.complete)
        self.assertEqual([p.id for p in result.pages], ["100", "101", "102", "103"])
        rules = result.pages[1]
        self.assertEqual((rules.parent_id, rules.version, rules.depth), ("100", "v3", 1))
        self.assertEqual(rules.body, "<p>Rules body</p>")
        self.assertEqual(rules.url, "https://w.example.test/wiki/spaces/S/pages/101")
        self.assertEqual(rules.labels, ["policy", "refund"])
        self.assertEqual(rules.attachments[0]["title"], "rules.pdf")

    def test_comments_are_read_only_when_asked(self):
        fake, plain = self.pull()
        self.assertFalse(any("comments" in c for c in fake.calls))
        _, with_comments = self.pull(comments=True)
        self.assertEqual(with_comments.pages[0].comments[0]["body"], "<p>ask legal</p>")

    def test_a_cursor_is_followed_to_the_end_and_never_capped_to_one_page(self):
        fake, result = self.pull()
        self.assertIn(f"{A}/pages/100/children?cursor=c2&limit=100", fake.calls)
        self.assertEqual({p.id for p in result.pages}, {"100", "101", "102", "103"})

    def test_a_page_limit_is_reported_as_incomplete_not_complete(self):
        _, result = self.pull(max_pages=2)
        self.assertFalse(result.complete)
        self.assertEqual(len(result.pages), 2)
        self.assertIn("stopped at 2 pages", result.note)

    def test_a_depth_limit_that_hides_children_is_reported(self):
        _, result = self.pull(max_depth=1)
        self.assertFalse(result.complete)
        self.assertEqual([p.id for p in result.pages], ["100", "101", "102"])
        self.assertIn("below depth 1", result.note)

    def test_a_next_link_to_another_origin_is_refused(self):
        for bad in ("https://evil.example.test/steal", "//evil.example.test/x", "/other/api"):
            routes = tree(
                {f"{A}/pages/100/children?limit=100": {"results": [], "_links": {"next": bad}}}
            )
            with self.assertRaisesRegex(wiki_rest.WikiError, "outside /wiki/"):
                self.pull(routes)

    def test_a_repeated_link_stops_instead_of_looping(self):
        loop = f"{A}/pages/100/children?limit=100"
        routes = tree({loop: {"results": [], "_links": {"next": loop}}})
        with self.assertRaisesRegex(wiki_rest.WikiError, "repeated"):
            self.pull(routes)

    def test_the_request_budget_is_a_hard_stop(self):
        client = wiki_rest.Client(Fake(tree()), max_requests=3)
        with self.assertRaisesRegex(wiki_rest.WikiError, "budget"):
            client.pull_tree("100", 50, 3)

    def test_a_page_id_must_be_digits(self):
        with self.assertRaises(ValueError):
            wiki_rest.Client(Fake({})).pull_tree("../etc", 5, 1)

    def test_bodies_and_comments_are_written_by_program_with_import_rows(self):
        _, result = self.pull(comments=True)
        with tempfile.TemporaryDirectory() as raw:
            rows = wiki_rest.write_pull(result, Path(raw), "REFUNDS")
            self.assertEqual((Path(raw) / "101.html").read_text(), "<p>Rules body</p>")
            self.assertEqual((Path(raw) / "101-comment-1.html").read_text(), "<p>ask legal</p>")
        rules = next(r for r in rows if r["remote_id"] == "101")
        self.assertEqual(
            (rules["source"], rules["source_version"], rules["parent_id"], rules["labels"]),
            ("wiki:REFUNDS/101", "v3", "100", "policy,refund"),
        )
        comment = next(r for r in rows if r["path"] == "101-comment-1.html")
        self.assertEqual((comment["parent_id"], comment["labels"]), ("101", "comment"))


class TransportTests(unittest.TestCase):
    def make(self, **kw):
        args = {
            "site": "https://w.example.test",
            "email": "a@example.test",
            "token": "s3cret-token",
        }
        args.update(kw)
        return wiki_rest.HttpTransport(**args)

    def test_only_an_https_origin_without_credentials_is_accepted(self):
        for bad in (
            {"site": "http://w.example.test"},
            {"site": "https://w.example.test/path"},
            {"site": "https://u:p@w.example.test"},
            {"site": "https://w.example.test?x=1"},
            {"email": ""},
            {"token": ""},
        ):
            with self.assertRaises(ValueError, msg=bad):
                self.make(**bad)

    def test_requests_are_get_only_and_stay_under_wiki(self):
        transport = self.make()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"results": []}'
        transport._opener = MagicMock()
        transport._opener.open.return_value = response
        self.assertEqual(transport.get(f"{A}/pages/1"), {"results": []})
        req = transport._opener.open.call_args[0][0]
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(req.full_url, "https://w.example.test" + f"{A}/pages/1")
        with self.assertRaises(wiki_rest.WikiError):
            transport.get("/rest/api/3/issue")

    def test_failures_never_echo_the_token(self):
        transport = self.make()
        transport._opener = MagicMock()
        transport._opener.open.side_effect = ConnectionError("boom s3cret-token")
        with self.assertRaises(wiki_rest.WikiError) as caught:
            transport.get(f"{A}/pages/1")
        self.assertNotIn("s3cret-token", str(caught.exception))

    def test_a_redirect_is_not_followed(self):
        handler = wiki_rest._NoRedirect()
        self.assertIsNone(
            handler.redirect_request(None, None, 302, "Found", {}, "https://evil.test")
        )


class PullScriptTests(WorkflowTestCase):
    def run_pull(self, routes=None, *extra, batch="p1"):
        argv = [
            "--batch-id",
            batch,
            "--root-page",
            "100",
            "--space",
            "REFUNDS",
            *extra,
            "--cwd",
            str(self.root),
        ]
        return wiki_pull.main(argv, Fake(tree() if routes is None else routes))

    def test_a_pull_writes_files_a_list_and_a_detail_manifest(self):
        self.assertEqual(self.run_pull(), 0)
        out = self.base / "_meta/work/pull-p1"
        with (out / "list.tsv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual([r["remote_id"] for r in rows], ["100", "101", "102", "103"])
        detail = json.loads((out / "pull.json").read_text())
        self.assertTrue(detail["complete"])
        self.assertEqual(detail["received_pages"], 4)
        self.assertEqual(detail["pages"][1]["attachments"][0]["title"], "rules.pdf")

    def test_the_pulled_list_feeds_a_bulk_import_dry_run(self):
        self.run_pull()
        out = self.base / "_meta/work/pull-p1"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "bulk_import.py"),
                "--batch-id",
                "i1",
                "--list-file",
                str(out / "list.tsv"),
                "--expected",
                "4",
                "--dry-run",
                "--cwd",
                str(self.root),
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)["items"]
        self.assertEqual([i["remote_id"] for i in plan], ["100", "101", "102", "103"])
        self.assertEqual(plan[1]["source_version"], "v3")

    def test_an_incomplete_pull_exits_four_and_still_writes_what_it_read(self):
        self.assertEqual(self.run_pull(None, "--max-pages", "2"), 4)
        detail = json.loads((self.base / "_meta/work/pull-p1/pull.json").read_text())
        self.assertFalse(detail["complete"])

    def test_invalid_requests_and_remote_failures_have_their_own_codes(self):
        self.assertEqual(self.run_pull(), 0)
        self.assertEqual(self.run_pull(batch="p1"), 2)  # batch folder exists
        self.assertEqual(
            wiki_pull.main(
                ["--batch-id", "p2", "--root-page", "../x", "--cwd", str(self.root)], Fake(tree())
            ),
            2,
        )
        self.assertEqual(self.run_pull({}, batch="p3"), 3)  # the wiki answers 404
