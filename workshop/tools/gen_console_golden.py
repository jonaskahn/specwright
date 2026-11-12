#!/usr/bin/env python3
"""Write the console's golden files: real data files plus the answers graph_query.py gives.

For a flat project (refund), a two-project program and a "trace" project that carries the whole
chain (business objective, epic, features, criteria, tasks, code, Jira) with deliberate gaps, this
builds the graph, writes every data kind through the shared writer, and records the expected
result of many graph queries computed by the Python implementation. The console's tests replay
the same queries in TypeScript.
"""

import argparse
import itertools
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "_shared" / "scripts"))

from kitlib import dataformat, graph, graph_query  # noqa: E402

FIXTURE = ROOT / "workshop" / "fixtures" / "refund" / "after-spec"
OUT = ROOT / "workshop" / "fixtures" / "console-golden"
EDGE = re.compile(r"^(-(\S+)->|<-(\S+)-) (\S+) \[([^/]*)/([^\]]*)\] ")
LEVEL = re.compile(r"^( *)(\S+) \((\S+)\)$")
HOP = re.compile(r"^(\S+) (-(\S+)->|<-(\S+)-) (\S+) \[([^/]*)/([^\]]*)\] ")


def make_flat(base: Path) -> Path:
    root = base / "flat"
    shutil.copytree(FIXTURE, root)
    return root


def make_program(base: Path) -> Path:
    root = base / "program" / ".specwright"
    for scope in ("REF", "ORD"):
        target = root / "projects" / scope
        shutil.copytree(FIXTURE, target)
        if scope == "ORD":
            for path in target.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".yaml", ".tsv"}:
                    path.write_text(path.read_text().replace("REF", "ORD"), encoding="utf-8")
    (root / "workspace.yaml").write_text(
        "mode: program\nprojects:\n- ORD\n- REF\ndefault_scope: ORD\n"
    )
    return root


TRACE_EPIC = """---
id: EPIC-001
type: epic
scope: REF
status: approved
title: Self-service refunds
updated: 2026-11-10
---
# Self-service refunds
"""
TRACE_BO = """---
id: BO-002
type: bo
scope: REF
status: approved
title: Cut manual approval work
updated: 2026-11-10
---
# Approval workload

Reviewers decide only the requests that need a person.
"""
TRACE_NOTIFY = """---
id: FEAT-003
type: feature
scope: REF
title: Tell the buyer the outcome
aliases: []
status: draft
bo: [BO-002]
updated: 2026-11-10
---
# Tell the buyer the outcome

## Goal
Buyers hear the result of a refund request without asking.

## Acceptance criteria
### AC-003-1 — Approval notice
Given request R100 is approved,
when the decision is saved,
then the buyer receives an approval message.

### AC-003-2 — Rejection notice
Given request R100 is rejected,
when the decision is saved,
then the buyer receives a rejection message with the reason.
"""


def tasks_file(feature: str, blocks: list[str]) -> str:
    head = f"---\nfeat: {feature}\nspec_hash: sha256:{'0' * 64}\nstatus: draft\n---\n## Tasks\n\n"
    return head + "\n".join(blocks)


def task(number: str, title: str, traces: str, touches: str = "") -> str:
    lines = [f"### TASK-{number} — {title}", f"Traces to: {traces}"]
    if touches:
        lines.append(f"Touches: {touches}")
    lines += [
        "Done when: the behaviour is observable.",
        "Stop and ask if: the rule is unclear.",
        "",
    ]
    return "\n".join(lines)


def make_trace(base: Path) -> Path:
    """An embedded project whose graph holds the full chain, with gaps a reader should see.

    Gaps on purpose: FEAT-003 is in no epic, FEAT-002 names no business objective, AC-003-2 has
    no task, TASK-001-3 implements nothing, one touched code file is missing, and FEAT-002
    mentions FEAT-009, which nothing defines.
    """
    root = base / "trace" / ".specwright"
    shutil.copytree(FIXTURE, root)
    code = base / "trace" / "src"
    code.mkdir()
    (code / "refund.py").write_text("# refund handling\n", encoding="utf-8")
    (code / "decide.py").write_text("# decisions\n", encoding="utf-8")
    (root / "01-analysis" / "epics").mkdir(parents=True)
    (root / "01-analysis" / "epics" / "EPIC-001.md").write_text(TRACE_EPIC, encoding="utf-8")
    (root / "01-analysis" / "BO-002.md").write_text(TRACE_BO, encoding="utf-8")
    drafts = root / "02-drafts"
    first = drafts / "FEAT-001.story.md"
    first.write_text(
        first.read_text().replace("bo: [BO-001]\n", "bo: [BO-001]\nepic: EPIC-001\n"),
        encoding="utf-8",
    )
    second = drafts / "FEAT-002.story.md"
    second.write_text(
        second.read_text()
        .replace("status: draft\n", "status: draft\nepic: EPIC-001\n")
        .replace(
            "## Open questions",
            "## Dependencies and relations\nNeeds FEAT-009.\n\n## Open questions",
        ),
        encoding="utf-8",
    )
    (drafts / "FEAT-003.story.md").write_text(TRACE_NOTIFY, encoding="utf-8")
    plan = root / "03-plan"
    (plan / "FEAT-001.tasks.md").write_text(
        tasks_file(
            "FEAT-001",
            [
                task("001-1", "Record an eligible request", "AC-001-1", "src/refund.py"),
                task(
                    "001-2",
                    "Refuse a duplicate",
                    "AC-001-1, AC-001-2",
                    "src/refund.py, src/notify.py",
                ),
                task("001-3", "Write a runbook", "FEAT-001"),
            ],
        ),
        encoding="utf-8",
    )
    (plan / "FEAT-002.tasks.md").write_text(
        tasks_file("FEAT-002", [task("002-1", "Approve a request", "AC-002-1", "src/decide.py")]),
        encoding="utf-8",
    )
    (plan / "FEAT-003.tasks.md").write_text(
        tasks_file("FEAT-003", [task("003-1", "Send the approval message", "AC-003-1")]),
        encoding="utf-8",
    )
    registry = root / "_meta" / "id-registry.md"
    rows = registry.read_text().splitlines()
    out = []
    for line in rows:
        if line.startswith("| REF:FEAT-001 "):
            line = line.replace("| story | — |", "| story | PROJ-101 |", 1)
        out.append(line)
    blank = " — |" * 10
    extra = [
        f"| REF:AC-003-1 | ac |{blank}",
        f"| REF:AC-003-2 | ac |{blank}",
        f"| REF:BO-002 | bo |{blank}",
        f"| REF:EPIC-001 | epic | PROJ-100 |{' — |' * 9}",
        f"| REF:FEAT-003 | story |{blank}",
    ]
    registry.write_text("\n".join(out + extra) + "\n", encoding="utf-8")
    return root


def export_all(root: Path) -> None:
    graph.build(root)
    for kind, spec in dataformat.KINDS.items():
        dataformat.write_kind(root, kind, spec.owner)


def none(text: str) -> str | None:
    return text or None


def neighbors(store, key, direction, rel=None, declared=False):
    rows = []
    for line in graph_query.neighbors(store, key, direction, rel, declared, 0, 1000):
        m = EDGE.match(line)
        side = "out" if m.group(2) else "in"
        rows.append([side, m.group(2) or m.group(3), m.group(4), m.group(5), none(m.group(6))])
    return rows


def levels(lines):
    out = []
    for line in lines:
        m = LEVEL.match(line)
        out.append([len(m.group(1)) // 2 + 1, m.group(2), m.group(3)])
    return out


def path(store, a, b):
    lines = graph_query.path(store, a, b, 6)
    if len(lines) == 1 and not HOP.match(lines[0]):
        return {"found": a == b, "hops": []}
    hops = []
    for line in lines:
        m = HOP.match(line)
        side = "out" if m.group(3) else "in"
        hops.append(
            [m.group(1), side, m.group(3) or m.group(4), m.group(5), m.group(6), none(m.group(7))]
        )
    return {"found": True, "hops": hops}


def cases(root: Path) -> list[dict]:
    store = graph_query.Store(root, None)
    keys = [n["key"] for n in store.nodes()]
    picks = [k for k in keys if any(m in k for m in (":FEAT-", ":AC-", ":Q-", ":CR-", ":BO-"))][:8]
    out: list[dict] = []
    for text, kind, status in (
        ("refund", None, None),
        ("", "feat", None),
        ("", None, "open"),
        ("request", "ac", None),
    ):
        rows = graph_query.find(store, text or None, kind, status, None, None, 0, 1000)
        out.append(
            {
                "type": "find",
                "args": {"text": text, "kind": kind, "status": status},
                "expect": [r.split(" ")[0] for r in rows],
            }
        )
    for key in picks:
        out.append(
            {
                "type": "neighbors",
                "args": {"key": key, "dir": "both"},
                "expect": neighbors(store, key, "both"),
            }
        )
        out.append(
            {
                "type": "neighbors",
                "args": {"key": key, "dir": "out", "declaredOnly": True},
                "expect": neighbors(store, key, "out", None, True),
            }
        )
        out.append(
            {
                "type": "up",
                "args": {"key": key},
                "expect": levels(graph_query.up(store, key, 0, 1000)),
            }
        )
        out.append(
            {
                "type": "down",
                "args": {"key": key, "depth": 3},
                "expect": levels(graph_query.down(store, key, 3, 0, 1000)),
            }
        )
        out.append(
            {"type": "impact", "args": {"key": key}, "expect": graph_query.impact(store, key)}
        )
    for a, b in itertools.combinations(picks, 2):
        out.append({"type": "path", "args": {"from": a, "to": b}, "expect": path(store, a, b)})
    return out


def write(variant: str, root: Path, out: Path = OUT) -> None:
    export_all(root)
    folder = out / variant
    shutil.rmtree(folder, ignore_errors=True)
    (folder / "data").mkdir(parents=True)
    for file in sorted((root / "_meta" / "data").glob("*.json")):
        text = file.read_text(encoding="utf-8").replace(str(root), "<root>")
        (folder / "data" / file.name).write_text(text, encoding="utf-8")
    (folder / "expected-queries.json").write_text(
        json.dumps(cases(root), indent=1) + "\n", encoding="utf-8"
    )
    print(f"wrote {folder}")


def generate(out: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        write("flat", make_flat(base), out)
        write("program", make_program(base), out)
        write("trace", make_trace(base), out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    generate(parser.parse_args(argv).out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
