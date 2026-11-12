"""Generated master index, crosswalk and read-first list.

Everything here is rebuilt from the graph by `graph build` and never edited by hand. Output is
sorted and carries no timestamp, so the same inputs always give the same bytes.
"""

from __future__ import annotations

import re
from pathlib import Path

from kitlib import schema, workspace
from kitlib.graph import BANNER, Graph, Node, clean, md_escape

INDEXED = (
    "snapshot",
    "idea",
    "epic",
    "feat",
    "q",
    "dec",
    "cr",
    "risk",
    "task",
    "asset",
    "diagram",
    "amendment",
    "candidates",
)
COLUMNS = ["key", "kind", "name", "aliases", "origin", "path", "status", "hash", "parent", "links"]
CROSSWALK_COLUMNS = [
    "legacy_id",
    "internal_key",
    "parent_group",
    "source_ids",
    "remote_id",
    "remote_url",
    "tracker_keys",
    "brief_row",
    "open_q",
    "dec_ids",
    "match",
]
RELATED = {"q", "dec", "snapshot", "feat", "cr", "amendment"}
STRUCTURAL = {"mentions", "has_ac", "has_task", "published_as", "last_snapshot", "external_parent"}
REGISTER = "01-analysis/baseline/register.tsv"
REGISTER_COLUMNS = ["legacy_id", "title", "group", "source_ref"]
FILES = ("INDEX.md", "index.tsv", "CROSSWALK.tsv", "READ-FIRST.md")


def cell(value: object) -> str:
    return re.sub(r"[\t\r\n]+", " ", str(value)).strip()


def _line(cells: list[object]) -> str:
    return "\t".join(cell(c) for c in cells)


def _flags(graph: Graph, node: Node, superseded: set[str]) -> str:
    flags = []
    life = node.extra.get("lifecycle", {})
    if life.get("blocked_by_q"):
        flags.append("blocked")
    if life.get("approval") in ("stale", "invalidated"):
        flags.append("stale")
    if node.status == "withdrawn":
        flags.append("withdrawn")
    if node.status == "superseded" or node.key in superseded:
        flags.append("superseded")
    if node.extra.get("content_class") in ("index-only", "empty"):
        flags.append("index-only")
    if not node.title.strip():
        flags.append("untitled")
    return ",".join([node.status, *flags]) if flags else node.status


def _parent(graph: Graph, node: Node) -> str:
    for rel in ("member_of", "shaped_from", "source_parent"):
        for e in graph.edges:
            if e.src == node.key and e.rel == rel and e.dst in graph.nodes:
                return e.dst
    return node.owner if node.owner and node.owner != node.key else ""


def rows(graph: Graph) -> list[list[str]]:
    nodes = graph.nodes
    superseded = {e.dst for e in graph.edges if e.rel == "supersedes"}
    outgoing: dict[str, set[str]] = {}
    for e in graph.edges:
        if e.rel in STRUCTURAL or e.src not in nodes or e.dst not in nodes:
            continue
        if nodes[e.dst].kind in RELATED:
            outgoing.setdefault(e.src, set()).add(f"{e.rel}:{e.dst}")
        if nodes[e.src].kind in RELATED:
            outgoing.setdefault(e.dst, set()).add(f"~{e.rel}:{e.src}")
    out = []
    for key in sorted(nodes):
        n = nodes[key]
        if n.kind not in INDEXED:
            continue
        loc = f"{n.path}:{n.line}" if n.path != "-" else "-"
        out.append(
            [
                key,
                n.kind,
                n.title,
                "|".join(n.extra.get("aliases", [])),
                n.extra.get("origin", ""),
                loc,
                _flags(graph, n, superseded),
                n.hash,
                _parent(graph, n),
                ",".join(sorted(outgoing.get(key, ()))),
            ]
        )
    return out


def read_register(path: Path) -> list[dict[str, str]] | None:
    """Legacy register rows, or None when the project has no register."""
    if not path.is_file():
        return None
    items: list[dict[str, str]] = []
    header: list[str] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        parts = [p.strip() for p in raw.split("\t")]
        if header is None:
            header = [p.lower() for p in parts]
            continue
        items.append({name: (parts[i] if i < len(parts) else "") for i, name in enumerate(header)})
    return items


def _tokens(node: Node) -> set[str]:
    found = [*node.extra.get("aliases", [])]
    for field in ("remote_id", "remote_url", "tracker_key"):
        if node.extra.get(field):
            found.append(str(node.extra[field]))
    return {t.strip().lower() for t in found if str(t).strip()}


def crosswalk(graph: Graph, root: Path, scopes: list[str]) -> list[list[str]]:
    nodes = graph.nodes
    out: list[list[str]] = []
    jira_of = {e.src: e.dst[5:] for e in graph.edges if e.rel == "published_as"}
    for scope in scopes:
        prefix = scope + ":"
        feats = {k: n for k, n in nodes.items() if k.startswith(prefix) and n.kind == "feat"}
        snaps = {k: n for k, n in nodes.items() if k.startswith(prefix) and n.kind == "snapshot"}
        by_alias: dict[str, list[str]] = {}
        for key, n in feats.items():
            for alias in n.extra.get("aliases", []):
                by_alias.setdefault(alias.strip().lower(), []).append(key)
        by_token: dict[str, list[str]] = {}
        for key, n in snaps.items():
            for token in _tokens(n):
                by_token.setdefault(token, []).append(key)
        register = read_register(workspace.scope_dir(root, scope) / REGISTER)
        if register is None:
            register = [
                {"legacy_id": n.extra["aliases"][0], "group": "", "source_ref": ""}
                for _, n in sorted(feats.items())
                if n.extra.get("aliases")
            ]
        used: set[str] = set()
        for item in register:
            legacy = item.get("legacy_id", "").strip()
            found = sorted(by_alias.get(legacy.lower(), []))
            tokens = {legacy.lower(), item.get("source_ref", "").strip().lower()}
            for key in found:
                tokens |= _tokens(feats[key])
            tokens.discard("")
            sources = sorted({s for t in tokens for s in by_token.get(t, [])})
            used.update(sources)
            first = feats[found[0]] if found else None
            if not found:
                match = "no-feature"
            elif len(found) > 1:
                match = "ambiguous"
            else:
                match = "matched" if sources else "no-source"
            group = item.get("group", "").strip() or (_parent(graph, first) if first else "")
            life = first.extra.get("lifecycle", {}) if first else {}
            snap = snaps[sources[0]] if sources else None
            out.append(
                [
                    legacy,
                    ",".join(found),
                    group,
                    ",".join(sources),
                    snap.extra.get("remote_id", "") if snap else "",
                    snap.extra.get("remote_url", "") if snap else "",
                    ",".join(
                        sorted(
                            (
                                {snaps[s].extra.get("tracker_key", "") for s in sources}
                                | {jira_of.get(f, "") for f in found}
                            )
                            - {""}
                        )
                    ),
                    next(
                        (
                            e.dst
                            for e in graph.edges
                            if found and e.src == found[0] and e.rel == "shaped_from"
                        ),
                        "",
                    ),
                    ",".join(life.get("open_q", [])),
                    ",".join(_decisions(graph, found)),
                    match,
                ]
            )
        if read_register(workspace.scope_dir(root, scope) / REGISTER) is not None:
            for key, n in sorted(snaps.items()):
                if key not in used and n.extra.get("remote_id"):
                    out.append(
                        [
                            "",
                            "",
                            "",
                            key,
                            n.extra.get("remote_id", ""),
                            n.extra.get("remote_url", ""),
                            n.extra.get("tracker_key", ""),
                            "",
                            "",
                            "",
                            "no-register",
                        ]
                    )
    return out


def _decisions(graph: Graph, feats: list[str]) -> list[str]:
    found = set()
    for e in graph.edges:
        is_decision = e.src in graph.nodes and graph.nodes[e.src].kind == "dec"
        if e.dst in feats and e.rel == "affects" and is_decision:
            found.add(e.src)
        if e.src in feats and e.rel == "member_of" and "DEC-" in e.file:
            found.add(f"{e.src.split(':')[0]}:{Path(e.file).name.split('--')[0].split('.')[0]}")
    return sorted(found)


def _md_row(cells: list[object]) -> str:
    return "| " + " | ".join(md_escape(clean(c, 400)) for c in cells) + " |"


def index_md(rows_: list[list[str]], label: str) -> str:
    kinds: dict[str, int] = {}
    for r in rows_:
        kinds[r[1]] = kinds.get(r[1], 0) + 1
    counts = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) or "empty"
    lines = [
        f"# Master index — {md_escape(label)}",
        "",
        f"> {BANNER}. Look an item up by any name with graph.py find or show.",
        "",
        f"{len(rows_)} artifacts: {counts}.",
        "",
        _md_row(COLUMNS),
        "|" + "|".join("---" for _ in COLUMNS) + "|",
    ]
    lines += [_md_row(r) for r in rows_]
    return "\n".join(lines) + "\n"


def read_first(graph: Graph, label: str) -> str:
    kinds: dict[str, int] = {}
    for n in graph.nodes.values():
        if n.kind in INDEXED:
            kinds[n.kind] = kinds.get(n.kind, 0) + 1
    counts = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) or "no artifacts yet"
    open_q = sum(1 for n in graph.nodes.values() if n.kind == "q" and n.status in schema.OPEN_Q)
    return "\n".join(
        [
            f"# Read first — {md_escape(label)}",
            "",
            f"> {BANNER}. Read these in order; stop when the question is answered.",
            "",
            f"Kit {schema.KIT_VERSION} · graph schema {schema.GRAPH_SCHEMA_VERSION} · "
            f"{counts} · {open_q} open question(s)",
            "",
            "1. Manifest: project.yaml (approvers, sources, limits, delivery target).",
            "2. Standing rules: AGENTS.md at the repository root, the only copy.",
            "3. Master index: _meta/INDEX.md, or _meta/index.tsv for scripts.",
            "4. Crosswalk: _meta/CROSSWALK.tsv maps every legacy or external name to its record.",
            "5. Status board: graph.py board.",
            "6. Open questions: graph.py find --kind q --status open (also --status proposed).",
            "7. Query the graph; do not open folders: graph.py show <any name>, "
            "graph.py context <item>, graph.py map.",
            "",
        ]
    )


def render(graph: Graph, root: Path, scopes: list[str], label: str) -> dict[str, str]:
    """The four generated files, keyed by file name inside `_meta/`."""
    data = rows(graph)
    index_tsv = "\n".join([f"# {BANNER}", "# " + "\t".join(COLUMNS), *map(_line, data)]) + "\n"
    cross = crosswalk(graph, root, scopes)
    cross_tsv = (
        "\n".join([f"# {BANNER}", "# " + "\t".join(CROSSWALK_COLUMNS), *map(_line, cross)]) + "\n"
    )
    return {
        "INDEX.md": index_md(data, label),
        "index.tsv": index_tsv,
        "CROSSWALK.tsv": cross_tsv,
        "READ-FIRST.md": read_first(graph, label),
    }
