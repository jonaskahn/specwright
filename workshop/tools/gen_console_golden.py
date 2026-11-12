#!/usr/bin/env python3
"""Write the console's golden files: real data files plus the answers graph_query.py gives.

For a flat project (refund) and a two-project program, this builds the graph, writes every data
kind through the shared writer, and records the expected result of many graph queries computed
by the Python implementation. The console's tests replay the same queries in TypeScript.
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    generate(parser.parse_args(argv).out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
