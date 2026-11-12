"""Question, decision, reservation, split and registry scripts: validated, logged and undoable."""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from kitlib import (
    frontmatter,
    graph,
    graph_query,
    miniyaml,
    recordops,
    rtm,
    schema,
    writelog,
)
from tests.test_workflow import WorkflowTestCase

SCRIPT = Path(__file__).resolve().parents[2] / "skills/_shared/scripts/record.py"
SNAPSHOT = (
    "---\nid: SRC-0001\ntype: snapshot\nstatus: raw\ntitle: Policy\naliases: []\n---\n"
    "Refunds close after 14 days.\n\nPayout needs approval.\n"
)
WHO = ["--decided-by-role", "PO", "--decided-by-name", "Lan", "--decided-by-account", "712020:aa11"]
URL = ["--evidence-kind", "url", "--evidence-ref", "https://example.test/minutes/1"]


class RecordTests(WorkflowTestCase):
    def setUp(self):
        super().setUp()
        (self.base / "00-inbox/SRC-0001.md").write_text(SNAPSHOT)
        self.ctx = recordops.Ctx(self.root, "REF", "sw-shape", today="2026-11-12")

    def edit_manifest(self, change):
        path = self.base / "project.yaml"
        data = miniyaml.loads(path.read_text())
        change(data)
        path.write_text(miniyaml.dumps(data))

    def snapshot_of_tree(self):
        return {
            p.relative_to(self.base).as_posix(): p.read_bytes()
            for p in sorted(self.base.rglob("*"))
            if p.is_file() and "_meta/graph" not in p.as_posix()
        }

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--cwd", str(self.root)],
            capture_output=True,
            text=True,
            timeout=60,
        )

    def make_question(self, **kwargs):
        values = {
            "title": "Which refund window applies",
            "affects": ["FEAT-001"],
            "owner": "PO",
            "raised_from": ["SRC-0001:L8"],
        }
        values.update(kwargs)
        plan = recordops.question_new(self.ctx, **values)
        recordops.execute(self.ctx, plan, "q-new", "REF:" + plan.made[0])
        return plan.made[0]

    # ---- questions

    def test_dry_run_writes_nothing(self):
        before = self.snapshot_of_tree()
        result = self.cli(
            "q", "new", "--title", "Window?", "--affects", "FEAT-001", "--owner", "PO", "--dry-run"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create records/Q-001--window.md", result.stdout)
        self.assertEqual(before, self.snapshot_of_tree())
        self.assertEqual(writelog.read(self.base / "_meta/write-log.md"), [])

    def test_question_is_named_cited_logged_and_counted_on_the_board(self):
        ident = self.make_question(quote="Refunds close after 14 days")
        path = self.base / "records/Q-001--which-refund-window-applies.md"
        self.assertEqual(ident, "Q-001")
        fm, body = frontmatter.split(path.read_text())
        self.assertEqual(fm["status"], "proposed")
        self.assertEqual(fm["affects"], ["FEAT-001"])
        self.assertRegex(fm["raised_from"][0], r"^SRC-0001:L8#[0-9a-f]{4}$")
        self.assertIn("> Refunds close after 14 days.", body)
        self.assertEqual(fm["sources"], ["SRC-0001"])
        entries = writelog.read(self.base / "_meta/write-log.md")
        self.assertEqual([e.kind for e in entries], ["INTENT", "RESULT"])
        self.assertTrue(any(f.startswith("file=records/Q-001--") for f in entries[1].fields))
        rows = graph_query.board(graph_query.Store(self.root, "REF"))
        row = next(r for r in rows if r["id"] == "REF:FEAT-001")
        self.assertEqual(row["blocked_by_q"], ["REF:Q-001"])
        self.assertEqual(writelog.drift(self.base / "_meta/write-log.md"), [])

    def test_invalid_questions_are_refused_before_any_write(self):
        before = self.snapshot_of_tree()
        cases = [
            {"affects": ["FEAT-099"]},
            {"affects": []},
            {"raised_from": ["SRC-0001:L99"]},
            {"raised_from": ["SRC-0001:L8"], "quote": "refunds never close"},
            {"due": "next week"},
            {"title": "  "},
        ]
        for case in cases:
            with self.assertRaises(recordops.RecordError, msg=case):
                values = {"title": "T", "affects": ["FEAT-001"], "owner": "PO", **case}
                recordops.question_new(self.ctx, **values)
        self.assertEqual(before, self.snapshot_of_tree())

    def test_a_withdrawn_question_keeps_its_id(self):
        self.make_question()
        plan = recordops.question_withdraw(self.ctx, "Q-001", "Duplicate of policy")
        recordops.execute(self.ctx, plan, "q-withdraw", "REF:Q-001")
        withdrawn = next((self.base / "records").glob("Q-001--*.md"))
        self.assertEqual(frontmatter.split(withdrawn.read_text())[0]["status"], "withdrawn")
        self.assertEqual(self.make_question(title="Second question"), "Q-002")
        with self.assertRaises(recordops.RecordError):
            recordops.question_withdraw(self.ctx, "Q-001", "again")

    def test_answering_records_a_decision_and_closes_the_question(self):
        self.make_question()
        who = recordops.decision_fields(
            self.ctx, "PO", "Lan", "712020:aa11", "url", "https://example.test/minutes/1"
        )
        plan = recordops.question_answer(self.ctx, "Q-001", "Use the 14 day window.", who)
        recordops.execute(self.ctx, plan, "q-answer", "REF:Q-001")
        q = frontmatter.split(next((self.base / "records").glob("Q-001--*.md")).read_text())[0]
        self.assertEqual((q["status"], q["decision"]), ("answered", "DEC-001"))
        dec = frontmatter.split(next((self.base / "records").glob("DEC-001--*.md")).read_text())[0]
        self.assertEqual(
            dec["decided_by"], {"role": "PO", "name": "Lan", "account_id": "712020:aa11"}
        )
        self.assertEqual((dec["answers"], dec["affects"]), (["Q-001"], ["FEAT-001"]))
        self.assertEqual(dec["evidence_url"], "https://example.test/minutes/1")
        rows = graph_query.board(graph_query.Store(self.root, "REF"))
        self.assertEqual(next(r for r in rows if r["id"] == "REF:FEAT-001")["open_q"], [])

    # ---- decisions

    def test_decisions_need_a_listed_decider_and_acceptable_evidence(self):
        def fields(
            role="PO", name="Lan", account="712020:aa11", kind="url", ref="https://e.test/1"
        ):
            return recordops.decision_fields(self.ctx, role, name, account, kind, ref)

        self.assertEqual(fields()["evidence_kind"], "url")
        for bad in (
            {"name": "Stranger"},
            {"role": "Dev"},
            {"name": ""},
            {"account": "someone-else"},
            {"kind": "chat", "ref": "https://chat.test/1"},  # chat is opt-in
            {"kind": "smoke-signal"},
            {"ref": ""},
            {"ref": "http://insecure.test"},
        ):
            with self.assertRaises(recordops.RecordError, msg=bad):
                fields(**bad)

    def test_chat_evidence_is_accepted_only_when_the_manifest_allows_it(self):
        self.edit_manifest(lambda data: data["evidence"]["allowed_kinds"].append("chat"))
        who = recordops.decision_fields(
            self.ctx, "PO", "Lan", "", "chat", "https://chat.test/thread/9"
        )
        self.assertEqual(who["evidence_kind"], "chat")
        with self.assertRaises(recordops.RecordError):
            recordops.decision_fields(self.ctx, "PO", "Lan", "", "chat", "thread 9")

    def test_without_approvers_a_decision_asks_for_setup(self):
        self.edit_manifest(lambda data: data.update(approvers=[]))
        with self.assertRaises(recordops.AskError):
            recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/1")
        result = self.cli("dec", "new", "--title", "T", "--affects", "FEAT-001", *WHO, *URL)
        self.assertEqual(result.returncode, 3)
        self.assertIn("approvers add", result.stderr)

    def test_a_new_decision_supersedes_an_older_one(self):
        who = recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/1")
        first, _ = recordops.decision_new(self.ctx, "Window is 14 days", ["FEAT-001"], who)
        recordops.execute(self.ctx, first, "dec-new", "REF:DEC-001")
        second, ident = recordops.decision_new(
            self.ctx, "Window is 30 days", ["FEAT-001"], who, supersedes=["DEC-001"]
        )
        recordops.execute(self.ctx, second, "dec-new", "REF:" + ident)
        old = frontmatter.split(next((self.base / "records").glob("DEC-001--*.md")).read_text())[0]
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(ident, "DEC-002")

    # ---- reservations, splits, registry

    def test_reserving_features_names_them_and_refuses_a_taken_alias(self):
        plan = recordops.reserve_features(self.ctx, ["Payout|LEG-300,payout-flow", "Cancel"])
        recordops.execute(self.ctx, plan, "reserve-feat", ", ".join(plan.made))
        self.assertEqual(plan.made, ["FEAT-002", "FEAT-003"])
        table = rtm.read_table(
            self.base / "_meta/id-registry.md", list(schema.REGISTRY_COLUMNS)
        ).table
        self.assertEqual(table.value("REF:FEAT-002", "Title"), "Payout")
        self.assertEqual(table.value("REF:FEAT-002", "Aliases"), "LEG-300|payout-flow")
        self.assertEqual(table.value("REF:FEAT-003", "State"), "reserved")
        with self.assertRaisesRegex(recordops.RecordError, "already names REF:FEAT-002"):
            recordops.reserve_features(self.ctx, ["Other|leg-300"])
        self.assertEqual(graph_query.Store(self.root, "REF").resolve("LEG-300"), "REF:FEAT-002")

    def test_accept_split_reserves_creates_and_decides_in_one_operation(self):
        who = recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/split")
        plan = recordops.accept_split(
            self.ctx, ["Payout|LEG-300", "Cancel|LEG-400"], ["FEAT-001"], [], "Refund journeys", who
        )
        warnings = recordops.execute(self.ctx, plan, "accept-split", ", ".join(plan.made))
        self.assertEqual(warnings, [])
        self.assertEqual(plan.made, ["EPIC-001", "FEAT-002", "FEAT-003", "DEC-001"])
        store = graph_query.Store(self.root, "REF")
        members = sorted(
            e.src for e in store.edges_for({"REF:EPIC-001"}, "in") if e.rel == "member_of"
        )
        self.assertEqual(members, ["REF:FEAT-001", "REF:FEAT-002", "REF:FEAT-003"])
        entries = writelog.read(self.base / "_meta/write-log.md")
        self.assertEqual([e.kind for e in entries], ["INTENT", "RESULT"])
        self.assertEqual(graph.check(self.root, "REF").count("REF: graph is stale; run build"), 0)

    def test_a_failed_split_undoes_every_write_and_logs_the_error(self):
        who = recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/split")
        before = self.snapshot_of_tree()
        plan = recordops.accept_split(self.ctx, ["Payout"], [], [], "Journeys", who)
        with (
            patch("kitlib.recordops.rtm.registry_upsert", side_effect=OSError("disk full")),
            self.assertRaises(OSError),
        ):
            recordops.execute(self.ctx, plan, "accept-split", "x")
        after = self.snapshot_of_tree()
        after.pop("_meta/write-log.md", None)
        before.pop("_meta/write-log.md", None)
        self.assertEqual(before, after)
        self.assertEqual(writelog.read(self.base / "_meta/write-log.md")[-1].fields[0], "error")
        self.assertEqual(writelog.unfinished(self.base / "_meta/write-log.md"), [])

    def test_accept_split_needs_url_evidence_and_active_epics(self):
        meeting = recordops.decision_fields(self.ctx, "PO", "Lan", "", "meeting", "minutes-7")
        with self.assertRaisesRegex(recordops.RecordError, "url evidence"):
            recordops.accept_split(self.ctx, ["A"], [], [], "E", meeting)
        who = recordops.decision_fields(self.ctx, "PO", "Lan", "", "url", "https://e.test/s")
        with self.assertRaisesRegex(recordops.RecordError, "not an active epic"):
            recordops.accept_split(self.ctx, ["A"], [], ["EPIC-009"], "", who)

    def test_register_follows_column_ownership(self):
        ok = self.cli("register", "FEAT-001", "--set", "Jira key=PROJ-9", "--as", "sw-publish")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        denied = self.cli("register", "FEAT-001", "--set", "Jira key=PROJ-8", "--as", "sw-shape")
        self.assertEqual(denied.returncode, 4)
        unknown = self.cli("register", "FEAT-001", "--set", "Colour=red")
        self.assertEqual(unknown.returncode, 2)
        table = rtm.read_table(
            self.base / "_meta/id-registry.md", list(schema.REGISTRY_COLUMNS)
        ).table
        self.assertEqual(table.value("REF:FEAT-001", "Jira key"), "PROJ-9")

    # ---- the command line

    def test_cli_creates_a_question_and_reports_json(self):
        result = self.cli(
            "q",
            "new",
            "--title",
            "Window?",
            "--affects",
            "FEAT-001",
            "--owner",
            "PO",
            "--raised-from",
            "SRC-0001:L8",
            "--format",
            "json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["made"], ["Q-001"])

    def test_cli_exit_codes_for_invalid_and_ask(self):
        bad = self.cli("q", "new", "--title", "T", "--affects", "FEAT-404", "--owner", "PO")
        self.assertEqual(bad.returncode, 2)
        self.assertIn("not defined or reserved", bad.stderr)
        bare = self.cli(
            "dec",
            "new",
            "--title",
            "T",
            "--affects",
            "FEAT-001",
            *WHO,
            "--evidence-kind",
            "chat",
            "--evidence-ref",
            "https://chat.test/1",
        )
        self.assertEqual(bare.returncode, 2)
        self.assertIn("does not accept chat", bare.stderr)
