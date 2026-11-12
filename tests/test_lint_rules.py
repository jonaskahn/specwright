"""Exercise rule decisions separately so unrelated findings cannot hide a regression."""

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kitlib import frontmatter, graph, hashing, schema, tables, workspace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/_shared/scripts/sw_lint.py"
module_spec = importlib.util.spec_from_file_location("specwright_lint", SCRIPT)
lint = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = lint
module_spec.loader.exec_module(lint)
GOOD = (ROOT / "fixtures/lint/good-story.md").read_text()
BO = (ROOT / "fixtures/lint/BO-001.md").read_text()


def doc(text=GOOD, path="02-drafts/FEAT-001.story.md"):
    return lint.Doc.from_text(path, text)


def update(text=GOOD, **values):
    return frontmatter.update(text, values)


def snapshot(text=GOOD):
    return update(
        text,
        id="SRC-0001",
        type="snapshot",
        status="raw",
        source_kind="jira-issue",
        spec_id="REF:FEAT-001",
        jira_status="To Do",
        repo_status="published",
    )


class RuleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def context(self, documents, **kwargs):
        return lint.Context(
            self.base,
            docs=documents,
            gate="publish",
            definitions=lint.definitions_for([*documents, doc(BO, "01-analysis/BO-001.md")], "REF"),
            **kwargs,
        )

    def findings(self, document, **kwargs):
        ctx = self.context([document], **kwargs)
        return lint.lint_document(document, ctx)

    def check_rule(self, rule, bad, good=None, **kwargs):
        good = good or doc()
        for label, document in (("bad", bad), ("good", good)):
            target = self.base / label / document.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(document.raw)
            self.assertEqual(lint.Doc.read(target, self.base / label).raw, document.raw)
        self.assertIn(rule, {f.rule for f in self.findings(bad, **kwargs)})
        self.assertNotIn(rule, {f.rule for f in self.findings(good, **kwargs)})

    def test_l001(self):
        self.check_rule("L-001", doc("---\nid: [\n---\n"))

    def test_l002(self):
        self.check_rule("L-002", doc(update(id="FEATURE-1")))

    def test_l003(self):
        self.check_rule("L-003", doc(GOOD.replace("### AC-001-2", "### AC-001-1")))

    def test_l004(self):
        self.check_rule("L-004", doc(GOOD + "\nBR-999\n"))

    def test_l005(self):
        self.check_rule("L-005", doc(update(bo=[])))

    def test_l006(self):
        self.check_rule("L-006", doc(GOOD.replace("### AC-001-2", "## Removed AC-001-2")))

    def test_l007(self):
        self.check_rule("L-007", doc(GOOD.replace("Given a parcel", "When a parcel")))

    def test_l008(self):
        self.check_rule(
            "L-008",
            doc(
                GOOD.replace("6 days", "several days").replace(
                    'status "Awaiting inspection"', "status awaiting inspection"
                )
            ),
        )

    def test_l009(self):
        self.check_rule("L-009", doc(GOOD.replace("the original price", "the FAST original price")))

    def test_l010(self):
        self.check_rule(
            "L-010",
            doc(
                GOOD.replace(
                    "Response time p95 is below 900 ms under 80 concurrent buyers, "
                    "measured over 10 minutes.",
                    "Performance is desired.",
                )
            ),
        )

    def test_l011(self):
        self.check_rule("L-011", doc(GOOD.replace("Example:", "Illustration:")))

    def test_l012(self):
        self.check_rule(
            "L-012", doc(GOOD.replace("States: default, empty, loading, error.", "A form."))
        )

    def test_l013(self):
        self.check_rule("L-013", doc(GOOD.replace("reason:", "because")))

    def test_l014(self):
        self.check_rule("L-014", doc(GOOD + "\n[NEEDS CLARIFICATION]\n"))

    def test_l015(self):
        self.check_rule(
            "L-015", doc(GOOD.replace("the original price", "the SQL database table price"))
        )

    def test_l016(self):
        self.check_rule("L-016", doc(update(status="raw")))

    def test_l017(self):
        self.check_rule("L-017", doc(GOOD.replace("AC-001-2", "AC-001-3")))

    def test_l018(self):
        self.check_rule(
            "L-018", doc(GOOD.replace("## Open questions\nNone", "## Open questions\nWho decides?"))
        )

    def test_l024(self):
        self.check_rule(
            "L-024",
            doc('<div style="border-left: 1px solid red">X</div>', "diagrams/a.html"),
            doc('<div style="border: 1px solid red">X</div>', "diagrams/a.html"),
        )

    def test_l037(self):
        registry = tables.Table(list(schema.REGISTRY_COLUMNS))
        registry.upsert("REF:FEAT-001", {"Jira key": "PROJ-14"})
        ctx = self.context([doc()], registry=registry)
        self.assertNotIn("L-037", {f.rule for f in lint.registry_findings(ctx)})
        registry.upsert("REF:FEAT-002", {"Jira key": "PROJ-14"})
        self.assertIn("L-037", {f.rule for f in lint.registry_findings(ctx)})

    def test_l038(self):
        snap = snapshot().replace(
            "Managed by specwright", "Draft hash: " + hashing.draft_hash(GOOD)
        )
        self.check_rule(
            "L-038",
            doc(snapshot(), "snapshots/jira/PROJ-14@1.md"),
            doc(snap, "snapshots/jira/PROJ-14@1.md"),
        )

    def test_l039(self):
        self.check_rule(
            "L-039",
            doc(snapshot(GOOD.replace("reason:", "because")), "snapshots/jira/PROJ-14@1.md"),
            doc(snapshot(), "snapshots/jira/PROJ-14@1.md"),
        )

    def test_l040(self):
        card = update(
            "---\nid: FEAT-001\ntype: feature\nstatus: published\n---\n## Sum"
            "mary\nReturn requests.\n",
            card=True,
            home="jira",
            links=["https://example.test/1"],
        )
        self.check_rule(
            "L-040",
            doc(update(card, links=[]), "02-drafts/FEAT-001.card.md"),
            doc(card, "02-drafts/FEAT-001.card.md"),
        )

    def test_l041(self):
        registry = tables.Table(list(schema.REGISTRY_COLUMNS))
        registry.upsert(
            "REF:FEAT-001",
            {
                "Last published draft hash": hashing.draft_hash(GOOD),
                "Last snapshot": "snapshots/jira/PROJ-14@1.md",
            },
        )
        self.check_rule(
            "L-041",
            doc(
                snapshot(GOOD.replace("the original price", "the paid price")),
                "snapshots/jira/PROJ-14@1.md",
            ),
            doc(snapshot(), "snapshots/jira/PROJ-14@1.md"),
            registry=registry,
        )

    def test_l042(self):
        registry = tables.Table(list(schema.REGISTRY_COLUMNS))
        registry.upsert("REF:FEAT-001", {"Last published draft hash": hashing.draft_hash(GOOD)})
        self.check_rule("L-042", doc(GOOD + "\n## New contract\nChanged text\n"), registry=registry)

    def test_l043(self):
        self.check_rule("L-043", doc(update(links=["http://example.test/1"])))

    def test_l044(self):
        self.check_rule(
            "L-044",
            doc(update(snapshot(), jira_status="Done"), "snapshots/jira/PROJ-14@1.md"),
            doc(snapshot(), "snapshots/jira/PROJ-14@1.md"),
        )

    def test_l045(self):
        self.check_rule("L-045", doc(GOOD.replace("the original price", "the paid price")))

    def test_l046(self):
        self.check_rule("L-046", doc(update(jira_summary="Beautiful return form")))

    def graph_ctx(self, built, root=False):
        if root:
            self.base.mkdir(parents=True, exist_ok=True)
            (self.base / "project.yaml").write_text("scope: REF\n")
            (self.base / "_meta").mkdir(parents=True, exist_ok=True)
            (self.base / "02-drafts").mkdir(parents=True, exist_ok=True)
            (self.base / "02-drafts/FEAT-001.story.md").write_text(GOOD)
        return self.context([doc()], built=built)

    def test_l047(self):
        g = graph.Graph(nodes={}, edges=[], inputs={})
        g.nodes["REF:feature/FEAT-001"] = graph.Node(
            "REF:feature/FEAT-001",
            "feature-file",
            "-",
            "x",
            "02-drafts/FEAT-001.feature",
            1,
            1,
            "-",
            "REF:FEAT-001",
            {"source_hash": "sha256:bad"},
        )
        g.nodes["REF:FEAT-001"] = graph.Node(
            "REF:FEAT-001",
            "feat",
            "-",
            "x",
            "02-drafts/FEAT-001.story.md",
            1,
            1,
            hashing.draft_hash(GOOD),
            "REF:FEAT-001",
        )
        self.assertIn("L-047", {f.rule for f in lint.graph_findings(self.graph_ctx(g, root=True))})

    def test_l048(self):
        g = graph.Graph(
            nodes={},
            edges=[
                graph.Edge(
                    "REF:TASK-001-1",
                    "implements",
                    "REF:AC-001-1",
                    "declared",
                    "03-plan/x.md",
                    1,
                    "unresolved",
                )
            ],
            inputs={},
        )
        g.nodes["REF:TASK-001-1"] = graph.Node(
            "REF:TASK-001-1", "task", "-", "x", "03-plan/x.md", 1, 1, "-", "REF:FEAT-001"
        )
        self.assertIn("L-048", {f.rule for f in lint.graph_findings(self.graph_ctx(g))})

    def test_l049(self):
        g = graph.Graph(nodes={}, edges=[], inputs={})
        (self.base / "_meta").mkdir(parents=True, exist_ok=True)
        self.assertIn("L-049", {f.rule for f in lint.graph_findings(self.graph_ctx(g, root=True))})

    def test_l050(self):
        g = graph.Graph(
            nodes={},
            edges=[
                graph.Edge(
                    "REF:FEAT-001",
                    "member_of",
                    "REF:EPIC-001",
                    "declared",
                    "02-drafts/x.md",
                    1,
                    "unresolved",
                )
            ],
            inputs={},
        )
        g.nodes["REF:FEAT-001"] = graph.Node(
            "REF:FEAT-001", "feat", "-", "x", "02-drafts/x.md", 1, 1, "-", "REF:FEAT-001"
        )
        self.assertIn("L-050", {f.rule for f in lint.graph_findings(self.graph_ctx(g))})

    def test_l051(self):
        g = graph.Graph(
            nodes={},
            edges=[
                graph.Edge(
                    "REF:FEAT-001",
                    "member_of",
                    "REF:EPIC-001",
                    "declared",
                    "02-drafts/x.md",
                    1,
                    "resolved",
                )
            ],
            inputs={},
        )
        g.nodes["REF:FEAT-001"] = graph.Node(
            "REF:FEAT-001", "feat", "-", "x", "02-drafts/x.md", 1, 1, "-", "REF:FEAT-001"
        )
        g.nodes["REF:EPIC-001"] = graph.Node(
            "REF:EPIC-001",
            "epic",
            "-",
            "x",
            "01-analysis/epics/EPIC-001.md",
            1,
            1,
            "-",
            "REF:EPIC-001",
            {"scopes": ["ORD"]},
        )
        self.assertIn("L-051", {f.rule for f in lint.graph_findings(self.graph_ctx(g))})

    def test_l052(self):
        g = graph.Graph(
            nodes={},
            edges=[
                graph.Edge(
                    "REF:TASK-001-1",
                    "touches",
                    "REF:code/x.py",
                    "declared",
                    "03-plan/x.md",
                    1,
                    "missing",
                )
            ],
            inputs={},
        )
        g.nodes["REF:TASK-001-1"] = graph.Node(
            "REF:TASK-001-1", "task", "-", "x", "03-plan/x.md", 1, 1, "-", "REF:FEAT-001"
        )
        self.assertIn("L-052", {f.rule for f in lint.graph_findings(self.graph_ctx(g))})

    def test_l053(self):
        reg = tables.Table(list(schema.REGISTRY_COLUMNS))
        reg.upsert("REF:FEAT-001", {"Last snapshot": "/tmp/x.md"})
        ctx = self.context([doc()], registry=reg)
        self.assertIn("L-053", {f.rule for f in lint.graph_findings(ctx)})

    def test_l054(self):
        self.check_rule("L-054", doc(GOOD.replace("aliases: []\n", "")))
        self.check_rule("L-054", doc(GOOD.replace("title: Submit a return request\n", "")))
        old_snapshot = snapshot().replace("aliases: []\n", "")
        found = [f for f in self.findings(doc(old_snapshot, "00-inbox/SRC-0001.md"))]
        self.assertEqual([f.sev for f in found if f.rule == "L-054"], ["warn"])

    def test_l055(self):
        self.check_rule("L-055", doc(update(title="TBD")))
        self.check_rule("L-055", doc(update(title="FEAT-001")))
        reg = tables.Table(list(schema.REGISTRY_COLUMNS))
        reg.upsert("REF:FEAT-005", {"Kind": "story"})
        bare = lint.registry_findings(self.context([doc()], registry=reg))
        self.assertIn("L-055", {f.rule for f in bare})
        reg.upsert("REF:FEAT-005", {"Title": "Payout"})
        named = lint.registry_findings(self.context([doc()], registry=reg))
        self.assertNotIn("L-055", {f.rule for f in named})

    def test_l057(self):
        from kitlib import cite

        inbox = self.base / "00-inbox"
        inbox.mkdir()
        lines = ["---", "id: SRC-0001", "---", "Refunds close after 14 days.", ""]
        (inbox / "SRC-0001.md").write_text("\n".join(lines) + "\n")
        stamp = cite.quote_hash([lines[3]])
        good = doc(GOOD + f"\nSource: SRC-0001:L4#{stamp}\n")
        for bad_text in (
            "SRC-0001:L9",  # beyond the end
            "SRC-0001:L5",  # blank line
            "SRC-0001:L4#ffff",  # text does not match the hash
            "SRC-0009:L1",  # no such snapshot
        ):
            self.check_rule("L-057", doc(GOOD + f"\nSource: {bad_text}\n"), good)

    def test_l057_weak_evidence_is_only_a_warning(self):
        inbox = self.base / "00-inbox"
        inbox.mkdir()
        (inbox / "SRC-0001.md").write_text(
            "---\nid: SRC-0001\ncontent_class: index-only\n---\ntext\n"
        )
        found = self.findings(doc(GOOD + "\nSource: SRC-0001:L5\n"))
        self.assertEqual([f.sev for f in found if f.rule == "L-057"], ["warn"])

    def test_l058(self):
        self.base.joinpath("old-notes").mkdir()
        self.base.joinpath(".git").mkdir()
        ctx = self.context([doc()])
        found = [f for f in lint.graph_findings(ctx) if f.rule == "L-058"]
        self.assertEqual([(f.sev, f.subject) for f in found], [("warn", "old-notes")])
        ctx.manifest = {"ignore_folders": ["old-notes"]}
        self.assertEqual([f for f in lint.graph_findings(ctx) if f.rule == "L-058"], [])

    def test_l059(self):
        head = "---\nid: Q-001\ntype: q\nscope: REF\ntitle: Window\naliases: []\nstatus: open\n"
        bad = doc(head + "---\n# Window\n", "records/Q-001.md")
        good = doc(head + "affects: [FEAT-001]\n---\n# Window\n", "records/Q-001.md")
        self.check_rule("L-059", bad, good)
        withdrawn = doc(head.replace("open", "withdrawn") + "---\n# Window\n", "records/Q-001.md")
        self.assertNotIn("L-059", {f.rule for f in self.findings(withdrawn)})

    def decision(self, extra):
        head = (
            "---\nid: DEC-001\ntype: dec\nscope: REF\ntitle: Window\naliases: []\n"
            "status: accepted\n"
        )
        return doc(head + extra + "---\n# Decision\n", "records/DEC-001.md")

    GOOD_WHO = (
        "decided_by:\n  role: PO\n  name: Lan\nevidence_kind: url\nevidence_ref: https://e.test/1\n"
    )

    def test_l060(self):
        self.check_rule("L-060", self.decision(""), self.decision(self.GOOD_WHO))
        no_evidence = self.decision("decided_by:\n  role: PO\n  name: Lan\n")
        self.assertIn("L-060", {f.rule for f in self.findings(no_evidence)})
        blank = self.decision(
            "decided_by:\n  role: PO\n  name: ''\nevidence_kind: url\nevidence_ref: x\n"
        )
        self.assertIn("L-060", {f.rule for f in self.findings(blank)})
        lifecycle = self.decision("subtype: lifecycle\norigin: local-transition\n")
        self.assertNotIn("L-060", {f.rule for f in self.findings(lifecycle)})
        waiver = self.decision("waives: L-009\n")
        self.assertNotIn("L-060", {f.rule for f in self.findings(waiver)})

    def test_l061(self):
        manifest = {"approvers": [{"role": "PO", "name": "Lan", "account_id": "1"}]}
        good = self.decision(self.GOOD_WHO)
        bad = self.decision(self.GOOD_WHO.replace("Lan", "Stranger"))
        self.assertNotIn("L-061", {f.rule for f in self.findings(good, manifest=manifest)})
        self.assertIn("L-061", {f.rule for f in self.findings(bad, manifest=manifest)})
        self.assertNotIn("L-061", {f.rule for f in self.findings(bad)})

    def test_l062(self):
        amendment = doc(
            "---\nid: AMD-001\ntype: amendment\nscope: REF\ntitle: Amend FEAT-001\naliases: []\n"
            "status: proposed\naffects: [FEAT-001]\n---\n## Current wording\n\n> a\n",
            "records/AMD-001.md",
        )
        feature = doc()
        self.assertIn(
            "L-062",
            {f.rule for f in lint.lint_document(feature, self.context([feature, amendment]))},
        )
        done = doc(
            amendment.raw.replace("status: proposed", "status: applied"), "records/AMD-001.md"
        )
        self.assertNotIn(
            "L-062", {f.rule for f in lint.lint_document(feature, self.context([feature, done]))}
        )

    def test_every_rule_has_a_named_test(self):
        covered = {"L-" + name.removeprefix("test_l") for name in dir(self) if re_rule(name)}
        self.assertEqual(lint.RULE_IDS, covered)

    def test_line_numbers_and_exempt_wording(self):
        text = GOOD.replace("the original price", "the FAST original price")
        finding = next(f for f in self.findings(doc(text)) if f.rule == "L-009")
        self.assertEqual(
            finding.line, next(n for n, s in enumerate(text.splitlines(), 1) if "FAST" in s)
        )
        safe = GOOD.replace(
            "## Goal\n", '## Goal\nShould have: Where returns apply, display "fast" and "should".\n'
        )
        safe = update(safe, priority="Should have", title="Fast returns")
        safe += "\n## Background\nThis used to be fast.\n"
        self.assertNotIn("L-009", {f.rule for f in self.findings(doc(safe))})
        bounded = GOOD.replace("the original price", "the breakfast price")
        self.assertNotIn("L-009", {f.rule for f in self.findings(doc(bounded))})

    def test_fences_tombstones_and_large_ordinal(self):
        text = GOOD.replace("AC-001-2", "AC-001-3").replace(
            "## Business rules", "~~AC-001-2~~ withdrawn\n## Business rules"
        )
        text += "\n~~~md\n### AC-999-4\n## Out of scope\nfast\n~~~\n"
        self.assertNotIn("L-017", {f.rule for f in self.findings(doc(text))})
        self.assertEqual(len(doc(text).ac), 2)
        self.assertIn(
            "L-017",
            {f.rule for f in self.findings(doc(GOOD.replace("AC-001-2", "AC-001-999999999999")))},
        )

    def test_waiver_targets_exact_id_only(self):
        bad = doc(GOOD.replace("reason:", "because"))
        decision = doc(
            "---\nid: DEC-001\ntype: dec\nstatus: accepted\nwaives: [L-013]\n"
            "applies_to: [FEAT-001]\nevidence: https://approval.test/1\n---\n"
            "Accepted exclusion.\n",
            "records/DEC-001.md",
        )
        ctx = self.context([bad, decision])
        lint.load_waivers(ctx)
        findings = lint.collect(ctx)
        self.assertTrue(next(f.waiver for f in findings if f.rule == "L-013"))
        ctx.docs[-1] = doc(decision.raw.replace("https://", "http://"), decision.path)
        ctx.waivers = []
        lint.load_waivers(ctx)
        self.assertFalse(ctx.waivers)

    def test_cr_suppresses_drift_not_signoff(self):
        bad = doc(GOOD.replace("the original price", "the paid price"))
        cr = doc(
            "---\nid: CR-001\ntype: cr\nstatus: proposed\naffected_ids: [FEAT"
            "-001]\n---\nReturn amount changes.\n",
            "records/CR-001.md",
        )
        registry = tables.Table(list(schema.REGISTRY_COLUMNS))
        registry.upsert("REF:FEAT-001", {"Last published draft hash": hashing.draft_hash(GOOD)})
        fs = lint.lint_document(bad, self.context([bad, cr], registry=registry))
        self.assertNotIn("L-042", {f.rule for f in fs})
        self.assertIn("L-045", {f.rule for f in fs})


def re_rule(name):
    return name.startswith("test_l") and name[6:].isdigit()


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        workspace.init(self.root, "flat", "REF", "Returns")
        (self.root / "02-drafts/FEAT-001.story.md").write_text(GOOD)
        (self.root / "01-analysis/BO-001.md").write_text(BO)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lint.main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def test_good_review_publish_and_report_determinism(self):
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        for gate in ("review", "publish"):
            code, text, err = self.cli("--gate", gate, "--format", "json")
            self.assertEqual((code, err), (0, ""), text)
        report = self.root / "_meta/lint-report.md"
        first = report.read_bytes()
        self.cli("--gate", "publish")
        self.assertEqual(first, report.read_bytes())
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertEqual(
            set(p for p in self.root.rglob("*") if p.is_file()) - before.keys(), {report}
        )

    def test_bad_story_and_all_gate_codes(self):
        bad = (ROOT / "fixtures/lint/bad-story.md").read_text()
        (self.root / "02-drafts/FEAT-001.story.md").write_text(bad)
        code, text, _ = self.cli("--format", "json")
        self.assertEqual(code, 20)
        rules = {f["rule"] for f in json.loads(text)["findings"]}
        self.assertTrue({"L-008", "L-009", "L-013"} <= rules)
        (self.root / "02-drafts/FEAT-001.story.md").write_text("---\nid: [\n---\n")
        for gate, expected in lint.GATES.items():
            self.assertEqual(self.cli("--gate", gate)[0], expected)

    def test_failure_is_loud_and_closed(self):
        with mock.patch.object(lint, "collect", side_effect=RuntimeError("checker unavailable")):
            code, text, err = self.cli()
        self.assertEqual(code, 2)
        self.assertEqual(text, "")
        self.assertIn("LINT FAILED CLOSED", err)
        with mock.patch.object(lint.fsio, "atomic_write", side_effect=OSError("read-only")):
            self.assertEqual(self.cli()[0], 2)

    def test_usage_help_and_missing_root(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            lint.main([])
        self.assertEqual(raised.exception.code, 2)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as raised:
            lint.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        shutil.rmtree(self.root / "02-drafts")
        (self.root / "project.yaml").unlink()
        self.assertEqual(self.cli()[0], 2)

    def test_program_selection_and_cross_scope_resolution(self):
        (self.root / "project.yaml").unlink()
        workspace.init(self.root, "program", "REF", "Returns")
        workspace.init(self.root, "program", "ORD", "Orders")
        selected = self.root / "projects/REF"
        (selected / "02-drafts/FEAT-001.story.md").write_text(GOOD.replace("BO-001", "ORD:BO-001"))
        (self.root / "projects/ORD/01-analysis/BO-001.md").write_text(BO.replace("REF", "ORD"))
        self.assertEqual(self.cli()[0], 2)
        code, text, _ = self.cli("--scope", "REF", "--format", "json")
        self.assertEqual(code, 0, text)
        self.assertTrue((selected / "_meta/lint-report.md").exists())
        self.assertFalse((self.root / "_meta/lint-report.md").exists())

    def test_bad_registry_and_invalid_utf8_are_findings(self):
        (self.root / "_meta/id-registry.md").write_text("| Wrong |\n|---|\n| x |\n")
        (self.root / "01-analysis/broken.md").write_bytes(b"\xff")
        code, text, _ = self.cli("--format", "json")
        self.assertEqual(code, 20)
        self.assertEqual(sum(f["rule"] == "L-001" for f in json.loads(text)["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
