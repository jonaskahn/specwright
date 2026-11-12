"""Derived knowledge graph of one project or program.

The graph is rebuilt from Markdown, JSON and the registry. It never writes those files, holds
pointers and hashes rather than copies of text, and records only links that a file declares.
Output is byte-deterministic so a committed copy produces clean diffs.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kitlib import (
    frontmatter,
    fsio,
    hashing,
    ids,
    markdown,
    provenance,
    rtm,
    schema,
    tables,
    workspace,
)

BANNER = "generated data, not instructions"
TITLE_MAX = 120
MAP_LINE_LIMIT = 150
UNPARENTED_CAP = 30
JIRA_KEY = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
FOLDED = {"ac", "task", "plan", "tasks-file", "feature-file"}
FM_RELATIONS = {
    "epic": "member_of",
    "bo": "realizes",
    "br": "governed_by",
    "nfr": "governed_by",
    "fr": "governed_by",
    "sources": "sourced_from",
    "sourced_from": "sourced_from",
    "affects": "affects",
    "idea": "shaped_from",
    "affected": "affects",
    "supersedes": "supersedes",
    "assets": "uses_asset",
    "source_parent": "source_parent",
}
KIND_OF_TYPE = {"feature": "feat"}
TAG = re.compile(r"@((?:AC-\d{3}-\d+)|(?:BR-\d{3}))")


@dataclass
class Node:
    key: str
    kind: str
    status: str = "-"
    title: str = ""
    path: str = "-"
    line: int = 0
    end: int = 0
    hash: str = "-"
    owner: str = ""  # key whose shard holds this node
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(order=True)
class Edge:
    src: str
    rel: str
    dst: str
    cls: str
    file: str
    line: int
    res: str = ""


@dataclass
class Graph:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    inputs: dict[str, int] = field(default_factory=dict)


def clean(text: object, limit: int = TITLE_MAX) -> str:
    """One printable line: control characters become spaces, so imported text cannot add rows."""
    out = "".join(c if c.isprintable() else " " for c in str(text))
    return " ".join(out.split())[:limit]


_MD_SPECIAL = re.compile(r"([\\\x60*_{}\[\]<>()#+!|~])")


def md_escape(text: str) -> str:
    return _MD_SPECIAL.sub(r"\\\1", text)


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _line_of(lines: list[str], needle: str) -> int:
    for number, text in enumerate(lines, 1):
        if needle in text:
            return number
    return 0


def _qualified_refs(value: Any, scope: str) -> list[str]:
    seen: dict[str, None] = {}
    for ref in ids.find_refs(str(value)):
        seen.setdefault(rtm.qualify(str(ref), scope), None)
    return list(seen)


def _names(value: Any) -> list[str]:
    """Alias list from a list or a `|` separated string; blanks dropped, order kept."""
    items = value if isinstance(value, list) else str(value or "").split("|")
    seen: dict[str, None] = {}
    for item in items:
        text = clean(item, 200)
        if text and text != "None":
            seen.setdefault(text, None)
    return list(seen)


def _identity_extra(fm: dict[str, Any]) -> dict[str, Any]:
    """Names and provenance the master index shows; only fields that are set."""
    extra: dict[str, Any] = {}
    aliases = _names(fm.get("aliases"))
    if aliases:
        extra["aliases"] = aliases
    origin = fm.get("origin") or fm.get("source") or ", ".join(_names(fm.get("sources")))
    if origin:
        extra["origin"] = clean(origin, 300)
    for field_name, target in (
        ("remote_id", "remote_id"),
        ("remote_url", "remote_url"),
        ("tracker_key", "tracker_key"),
        ("content_class", "content_class"),
    ):
        if fm.get(field_name):
            extra[target] = clean(fm[field_name], 300)
    return extra


def is_blocking(fm: dict) -> bool:
    """A question blocks its features unless it says otherwise."""
    return str(fm.get("blocking", True)).strip().lower() not in ("false", "no", "0")


def declared_affects(fm: dict, scope: str) -> set[str]:
    """Qualified IDs named in `affects` (or older `affected`); body mentions do not count."""
    out: set[str] = set()
    for name in ("affects", "affected"):
        out.update(_qualified_refs(fm.get(name, ""), scope))
    return out


def open_questions(graph: Graph) -> dict[str, list[tuple[str, bool]]]:
    """Open questions per feature from declared `affects` edges only: (question, blocking)."""
    found: dict[str, list[tuple[str, bool]]] = {}
    for e in graph.edges:
        src = graph.nodes.get(e.src)
        dst = graph.nodes.get(e.dst)
        if e.rel != "affects" or e.cls != "declared" or not src or not dst:
            continue
        if src.kind == "q" and src.status in schema.OPEN_Q and dst.kind == "feat":
            found.setdefault(e.dst, []).append((e.src, bool(src.extra.get("blocking", True))))
    return {k: sorted(set(v)) for k, v in found.items()}


def input_files(root: Path, scopes: list[str]) -> list[Path]:
    """Every file the graph reads, sorted; raw sources and the graph itself are excluded."""
    out: list[Path] = []
    manifests = [root / workspace.PROGRAM_MANIFEST, root / workspace.FLAT_MANIFEST]
    out += [p for p in manifests if p.is_file()]
    for scope in scopes:
        base = workspace.scope_dir(root, scope)
        if base != root:
            out.append(base / workspace.FLAT_MANIFEST)
        for folder, pattern in (
            ("01-analysis", "*.md"),
            ("02-drafts", "*.md"),
            ("02-drafts", "*.feature"),
            ("03-plan", "*.md"),
            ("records", "*.md"),
            ("snapshots", "*.md"),
            ("diagrams", "*.json"),
            ("01-analysis/baseline", "*.tsv"),
            ("01-analysis/candidates", "*.tsv"),
        ):
            for path in sorted((base / folder).rglob(pattern)):
                if path.is_file() and not path.is_symlink():
                    out.append(path)
        out.append(base / "_meta/id-registry.md")
        out.append(base / "_meta/asset-registry.md")
        out.append(base / "_meta/lifecycle-pending.json")
        out.extend(sorted((base / "_meta/provenance").glob("SRC-*.jsonl")))
        out.extend(p for p in (base / "00-inbox").glob("SRC-*.md") if not p.is_symlink())
    return sorted({p for p in out if p.is_file()})


def digest(root: Path, files: list[Path]) -> str:
    h = hashlib.sha256()
    for path in files:
        h.update(_rel(path, root).encode() + b"\0" + path.read_bytes() + b"\0")
    return "sha256:" + h.hexdigest()


def _title(fm: dict[str, Any], body: str) -> str:
    for key in ("title", "jira_summary"):
        if fm.get(key):
            return clean(fm[key])
    for line in body.splitlines():
        if line.startswith("# "):
            return clean(line[2:])
    return ""


def collect(root: Path, scopes: list[str], known: list[str]) -> Graph:
    """Nodes and edges for scopes; targets in scopes outside known are scope-not-loaded."""
    graph = Graph()
    entities, findings = rtm.scan(root)
    graph.findings += [f for f in findings if f.split(":")[0] in scopes or ":" not in f]
    for scope in scopes:
        manifest = workspace.load(workspace.scope_dir(root, scope) / workspace.FLAT_MANIFEST)
        base = workspace.scope_dir(root, scope)
        for name in workspace.stray_folders(base, manifest.get("ignore_folders") or []):
            graph.findings.append(f"{scope}: stray folder {name}/ is not read as evidence")
    texts: dict[Path, tuple[list[str], Any]] = {}

    def read(path: Path):
        if path not in texts:
            raw = path.read_text(encoding="utf-8")
            texts[path] = (raw.splitlines(), frontmatter.parse(raw))
        return texts[path]

    for key, entity in sorted(entities.items()):
        scope = key.split(":")[0]
        if scope not in scopes:
            continue
        lines, parsed = read(entity.path)
        rel = _rel(entity.path, root)
        if entity.kind == "ac":
            _add_ac(graph, entity, parsed, rel)
            continue
        if entity.kind == "task":
            _add_task(graph, entity, root, rel)
            continue
        kind = KIND_OF_TYPE.get(entity.kind, entity.kind)
        node = Node(
            key,
            kind,
            str(entity.fm.get("status", "-")),
            _title(entity.fm, entity.body),
            rel,
            1,
            len(lines),
            hashing.draft_hash(entity.path.read_text(encoding="utf-8")),
            key,
        )
        if kind == "epic":
            node.extra["scopes"] = [str(s) for s in entity.fm.get("scopes") or [scope]]
        if kind == "q":
            node.extra["blocking"] = is_blocking(entity.fm)
        node.extra.update(
            _identity_extra(
                provenance.effective(workspace.scope_dir(root, scope), entity.fm["id"], entity.fm)
                if kind == "snapshot"
                else entity.fm
            )
        )
        graph.nodes[key] = node
        declared: set[str] = set()
        for fm_key, rel_name in FM_RELATIONS.items():
            if kind == "dec" and fm_key == "epic":
                continue  # a decision records membership; it is not itself a member
            for target in _qualified_refs(entity.fm.get(fm_key, ""), scope):
                if target != key:
                    declared.add(target)
                    graph.edges.append(
                        Edge(
                            key,
                            rel_name,
                            target,
                            "declared",
                            rel,
                            _line_of(lines, target.split(":")[1]),
                        )
                    )
        for target in sorted(entity.refs - declared - {key}):
            graph.edges.append(
                Edge(
                    key, "mentions", target, "mentioned", rel, _line_of(lines, target.split(":")[1])
                )
            )
        parent = str(entity.fm.get("jira_parent", "None"))
        if kind == "feat" and JIRA_KEY.match(parent):
            graph.nodes.setdefault(f"jira:{parent}", Node(f"jira:{parent}", "jira", owner=""))
            graph.edges.append(
                Edge(
                    key,
                    "external_parent",
                    f"jira:{parent}",
                    "declared",
                    rel,
                    _line_of(lines, parent),
                    "external",
                )
            )
    for scope in scopes:
        _scope_artifacts(graph, root, scope, entities)
        _registry_edges(graph, root, scope, entities)
    _lifecycle_nodes(graph, root, scopes)
    _resolve(graph, known)
    graph.edges.sort()
    graph.inputs = {_rel(p, root): p.stat().st_size for p in input_files(root, known)}
    return graph


def _add_ac(graph: Graph, entity: rtm.Entity, parsed: Any, rel: str) -> None:
    scope = entity.key.split(":")[0]
    section = markdown.sections(parsed.body, first_line=parsed.body_line).get("Acceptance criteria")
    blocks = markdown.ac_blocks(section)
    ac = entity.key.split(":")[1]
    block = blocks.get(ac)
    line = block.line if block else 0
    end = line + (block.text.count(chr(10)) if block else 0)
    owner = entity.parent or ""
    graph.nodes[entity.key] = Node(
        entity.key,
        "ac",
        "withdrawn" if entity.withdrawn else "active",
        clean(block.title) if block else "",
        rel,
        line,
        end,
        "-",
        owner,
    )
    graph.edges.append(Edge(owner, "has_ac", entity.key, "structural", rel, line, "resolved"))
    _ = scope


def _add_task(graph: Graph, entity: rtm.Entity, root: Path, rel: str) -> None:
    scope = entity.key.split(":")[0]
    details = entity.fm
    line = int(details.get("line", 0))
    owner = entity.parent or ""
    graph.nodes[entity.key] = Node(
        entity.key,
        "task",
        "withdrawn" if entity.withdrawn else "active",
        clean(details.get("title", "")),
        rel,
        line,
        line,
        "-",
        owner,
    )
    graph.edges.append(Edge(owner, "has_task", entity.key, "structural", rel, line, "resolved"))
    for target in sorted(entity.refs - {owner}):
        graph.edges.append(Edge(entity.key, "implements", target, "declared", rel, line))
    touches = [t.strip() for t in str(details.get("touches", "")).split(",") if t.strip()]
    base = workspace.scope_dir(root, scope)
    for item in touches:
        graph.edges.append(_touch_edge(root, scope, base, entity.key, item, rel, line, graph))


def _touch_edge(
    root: Path, scope: str, base: Path, task: str, item: str, rel: str, line: int, graph: Graph
) -> Edge:
    try:
        folder = workspace.code_root(root, scope)
    except workspace.WorkspaceError:
        folder = None
    repo = workspace.code_repo_root(root)
    dst = f"{scope}:code/{item}"
    if repo is None or folder is None:
        res = "no-code-root"
    else:
        try:
            target = workspace.safe_join(repo, item)
            res = "exists" if target.exists() else "missing"
        except workspace.WorkspaceError:
            res, dst = "unsafe-path", f"{scope}:code/!rejected"
    if res in ("exists", "missing"):
        graph.nodes.setdefault(dst, Node(dst, "code", res, item, item, 0, 0, "-", ""))
        graph.nodes[dst].status = res
    return Edge(task, "touches", dst, "declared", rel, line, res)


def _scope_artifacts(graph: Graph, root: Path, scope: str, entities: dict[str, Any]) -> None:
    base = workspace.scope_dir(root, scope)

    def feat_key(name: str) -> str:
        return f"{scope}:{name}"

    for path in sorted((base / "diagrams").glob("*.json")):
        if path.is_symlink():
            continue
        rel = _rel(path, root)
        key = f"{scope}:diagram/{path.stem}"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            graph.findings.append(f"{rel}: diagram is not valid JSON")
            continue
        graph.nodes[key] = Node(
            key,
            "diagram",
            "-",
            clean(data.get("title", path.stem)) if isinstance(data, dict) else "",
            rel,
            1,
            0,
            hashing.bytes_hash(path.read_bytes()),
            key,
        )
        lines = path.read_text(encoding="utf-8").splitlines()
        for target in sorted(_spec_ids(data, scope)):
            graph.edges.append(
                Edge(
                    key,
                    "illustrates",
                    target,
                    "declared",
                    rel,
                    _line_of(lines, target.split(":")[1]),
                )
            )
    _asset_registry_edges(graph, root, base, scope)
    for path in sorted((base / "02-drafts").glob("*.feature")):
        if path.is_symlink():
            continue
        feat = feat_key(path.name.split(".")[0])
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        key = f"{scope}:feature/{path.name.split('.')[0]}"
        match = re.search(r"source-hash:\s*(sha256:[0-9a-f]+)", text)
        node = Node(
            key, "feature-file", "-", path.name, rel, 1, len(lines), hashing.text_hash(text), feat
        )
        node.extra["source_hash"] = match.group(1) if match else "UNKNOWN"
        graph.nodes[key] = node
        graph.edges.append(Edge(key, "derives_from", feat, "declared", rel, 1))
        for number, line in enumerate(lines, 1):
            for tag in TAG.findall(line):
                graph.edges.append(
                    Edge(key, "exercises", f"{scope}:{tag}", "declared", rel, number)
                )
    for path in sorted((base / "03-plan").glob("*.md")):
        if path.is_symlink():
            continue
        rel = _rel(path, root)
        text = path.read_text(encoding="utf-8")
        parsed = frontmatter.parse(text)
        name = path.name.split(".")[0]
        kind = "tasks-file" if path.name.endswith(".tasks.md") else "plan"
        feat = feat_key(str((parsed.fm or {}).get("feat", name)).split(":")[-1])
        key = f"{scope}:{'tasks' if kind == 'tasks-file' else 'plan'}/{name}"
        node = Node(
            key,
            kind,
            str((parsed.fm or {}).get("status", "-")),
            path.name,
            rel,
            1,
            len(text.splitlines()),
            hashing.draft_hash(text),
            feat,
        )
        node.extra["spec_hash"] = str((parsed.fm or {}).get("spec_hash", "UNKNOWN"))
        graph.nodes[key] = node
        graph.edges.append(Edge(key, "derives_from", feat, "declared", rel, 1))


def _asset_registry_edges(graph: Graph, root: Path, base: Path, scope: str) -> None:
    """Read the asset registry; assets are reference material, never instructions."""
    path = base / "_meta/asset-registry.md"
    if not path.is_file():
        return
    try:
        doc = rtm.read_table(path, list(schema.ASSET_REGISTRY_COLUMNS))
    except (OSError, ValueError):
        graph.findings.append(f"{_rel(path, root)}: asset registry unreadable")
        return
    rel = _rel(path, root)
    file_col, kind_col, hash_col, refs_col, state_col = (
        doc.table.col("File"),
        doc.table.col("Kind"),
        doc.table.col("sha256"),
        doc.table.col("Refs"),
        doc.table.col("State"),
    )
    for row in doc.table.rows:
        key = row[0]
        asset_id = key.split(":")[-1]
        file_name = row[file_col]
        kind = row[kind_col] or "other"
        state = row[state_col] or "captured"
        node_key = f"{scope}:asset/{asset_id}"
        graph.nodes[node_key] = Node(
            node_key,
            "asset",
            state,
            file_name or asset_id,
            file_name if file_name else "-",
            0,
            0,
            row[hash_col] or "-",
            "",
        )
        graph.nodes[node_key].extra["kind"] = kind
        for ref_text in str(row[refs_col]).split(","):
            for target in _qualified_refs(ref_text, scope):
                graph.edges.append(Edge(node_key, "supports", target, "declared", rel, 0))


def _spec_ids(data: Any, scope: str) -> set[str]:
    found: set[str] = set()
    if isinstance(data, dict):
        for name, value in data.items():
            if name == "spec_ids" and isinstance(value, list):
                for item in value:
                    found.update(_qualified_refs(item, scope))
            else:
                found |= _spec_ids(value, scope)
    elif isinstance(data, list):
        for item in data:
            found |= _spec_ids(item, scope)
    return found


def _registry_edges(graph: Graph, root: Path, scope: str, entities: dict[str, Any]) -> None:
    base = workspace.scope_dir(root, scope)
    path = base / "_meta/id-registry.md"
    try:
        doc = rtm.read_table(path, list(schema.REGISTRY_COLUMNS))
    except (OSError, ValueError):
        graph.findings.append(f"{_rel(path, root)}: registry unreadable")
        return
    rel = _rel(path, root)
    jira_col, snap_col, kind_col = (doc.table.col(c) for c in ("Jira key", "Last snapshot", "Kind"))
    epic_of: dict[str, str] = {}
    for row in doc.table.rows:
        key, jira = row[0], row[jira_col]
        if jira and jira not in ("—", "unknown") and JIRA_KEY.match(jira):
            graph.nodes.setdefault(f"jira:{jira}", Node(f"jira:{jira}", "jira"))
            graph.edges.append(
                Edge(key, "published_as", f"jira:{jira}", "registry", rel, 0, "external")
            )
            if row[kind_col] == "epic":
                epic_of[jira] = key
        snap = row[snap_col]
        if snap and snap not in ("—", "unknown"):
            sk = f"snapshot:{snap}"
            graph.nodes.setdefault(sk, Node(sk, "snapshot-file", "-", clean(snap), clean(snap)))
            graph.edges.append(Edge(key, "last_snapshot", sk, "registry", rel, 0, "external"))
    for edge in list(graph.edges):
        if edge.rel == "external_parent" and edge.dst[5:] in epic_of:
            graph.edges.append(
                Edge(edge.src, "member_of", epic_of[edge.dst[5:]], "registry", rel, 0)
            )


def _lifecycle_nodes(graph: Graph, root: Path, scopes: list[str]) -> None:
    from kitlib import lifecycle

    for scope in scopes:
        base = workspace.scope_dir(root, scope)
        registry_path = base / "_meta/id-registry.md"
        registry = tables.parse(registry_path.read_text(encoding="utf-8")).table
        if registry:
            for row in registry.rows:
                key = row[0]
                if not key.startswith(scope + ":") or not ids.matches_type(
                    "feature", key.split(":")[-1]
                ):
                    continue
                if key not in graph.nodes:
                    state = registry.get(key, "State")
                    state = state if state in ("withdrawn", "superseded") else "reserved"
                    graph.nodes[key] = Node(
                        key,
                        "feat",
                        state,
                        registry.value(key, "Title"),
                        _rel(registry_path, root),
                        0,
                        0,
                        "-",
                        key,
                    )
                    aliases = _names(registry.value(key, "Aliases"))
                    if aliases:
                        graph.nodes[key].extra["aliases"] = aliases
                    if registry.value(key, "Source ref"):
                        graph.nodes[key].extra["origin"] = registry.value(key, "Source ref")
        for record_path in sorted((base / "records").glob("DEC-*.md")):
            record = frontmatter.parse(record_path.read_text(encoding="utf-8")).fm or {}
            if record.get("subtype") != "accepted-split" or record.get("status") != "accepted":
                continue
            listed = record.get("epics") or [record.get("epic", "")]
            epics = [str(e) for e in listed if str(e)] or [""]
            if not record.get("evidence_url") or any(
                e not in graph.nodes or graph.nodes[e].kind != "epic" for e in epics
            ):
                graph.findings.append(f"{record_path.name}: invalid accepted split membership")
                continue
            for epic in epics:
                for key in record.get("features") or []:
                    if key in graph.nodes and graph.nodes[key].kind == "feat":
                        graph.edges.append(
                            Edge(key, "member_of", epic, "declared", _rel(record_path, root), 1)
                        )
        pending = open_questions(graph)
        for node in list(graph.nodes.values()):
            if not node.key.startswith(scope + ":"):
                continue
            if node.kind == "feat":
                item = lifecycle.feature(base, node.key, node.status)
                asked = pending.get(node.key, [])
                item["open_q"] = [q for q, _ in asked]
                item["blocked_by_q"] = [q for q, blocking in asked if blocking]
                node.extra["lifecycle"] = item
            elif node.kind == "epic":
                node.extra["station"] = "accepted" if node.status == "approved" else "shape"


def _resolve(graph: Graph, known: list[str]) -> None:
    for edge in graph.edges:
        if edge.res:
            continue
        target = graph.nodes.get(edge.dst)
        if target is not None:
            edge.res = "withdrawn" if target.status == "withdrawn" else "resolved"
            continue
        scope = edge.dst.split(":")[0]
        edge.res = "unresolved" if scope in known or ":" not in edge.dst else "scope-not-loaded"


def build_graph(root: Path, scopes: list[str], known: list[str] | None = None) -> Graph:
    """Collect for scopes. A scope graph built alone treats other scopes as not loaded."""
    return collect(root, scopes, known or scopes)


# ---- rendering -------------------------------------------------------------------------------


def _tsv(*cells: object) -> str:
    return "\t".join(clean(c, 400) if not isinstance(c, int) else str(c) for c in cells)


def _render_files(graph: Graph, root: Path, label: str, scopes: list[str]) -> dict[str, str]:
    files: dict[str, str] = {}
    nodes = graph.nodes
    out_edges = sorted(graph.edges)
    in_edges = sorted(graph.edges, key=lambda e: (e.dst, e.rel, e.src, e.cls, e.line))
    head = f"# {BANNER}\n"
    index = [head + "# key\tkind\tstatus\ttitle\tshard\tpath:line\taliases"]
    for key in sorted(nodes):
        n = nodes[key]
        owner = n.owner or (key if n.kind not in ("jira", "code", "snapshot-file") else "")
        shard = f"shards/{_shard_kind(nodes, owner)}/{_safe(owner)}.json" if owner else "-"
        loc = f"{n.path}:{n.line}" if n.path != "-" else "-"
        index.append(
            _tsv(key, n.kind, n.status, n.title, shard, loc, "|".join(n.extra.get("aliases", [])))
        )
    files["index.tsv"] = "\n".join(index) + "\n"
    cols = "# from\trel\tto\tclass\tfile\tline\tresolution"
    for name, rows in (("edges-out.tsv", out_edges), ("edges-in.tsv", in_edges)):
        body = [head + cols]
        body += [_tsv(e.src, e.rel, e.dst, e.cls, e.file, e.line, e.res) for e in rows]
        files[name] = "\n".join(body) + "\n"
    counts_out: dict[str, dict[str, int]] = {}
    counts_in: dict[str, dict[str, int]] = {}
    for e in graph.edges:
        counts_out.setdefault(e.src, {}).setdefault(e.rel, 0)
        counts_out[e.src][e.rel] += 1
        counts_in.setdefault(e.dst, {}).setdefault(e.rel, 0)
        counts_in[e.dst][e.rel] += 1
    children: dict[str, list[str]] = {}
    for key, n in nodes.items():
        if n.owner and n.owner != key:
            children.setdefault(n.owner, []).append(key)
    jira_of = {e.src: e.dst[5:] for e in graph.edges if e.rel == "published_as"}
    for key in sorted(nodes):
        n = nodes[key]
        if n.owner and n.owner != key:
            continue
        if n.kind in ("jira", "code", "snapshot-file"):
            continue
        shard = {
            "banner": BANNER,
            "key": key,
            "kind": n.kind,
            "status": n.status,
            "title": n.title,
            "path": n.path,
            "line": n.line,
            "end": n.end,
            "hash": n.hash,
            "jira": jira_of.get(key, "UNKNOWN"),
            "edges_out": dict(sorted(counts_out.get(key, {}).items())),
            "edges_in": dict(sorted(counts_in.get(key, {}).items())),
            "children": [
                {
                    "key": c,
                    "kind": nodes[c].kind,
                    "status": nodes[c].status,
                    "title": nodes[c].title,
                    "path": nodes[c].path,
                    "line": nodes[c].line,
                    "end": nodes[c].end,
                    "hash": nodes[c].hash,
                    **nodes[c].extra,
                }
                for c in sorted(children.get(key, []))
            ],
            **n.extra,
        }
        files[f"shards/{n.kind}/{_safe(key)}.json"] = (
            json.dumps(shard, indent=1, sort_keys=True) + "\n"
        )
    map_text, pages = _render_map(graph, root, label)
    files["KNOWLEDGE-MAP.md"] = map_text
    files.update(pages)
    return files


def _safe(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", key)


def _shard_kind(nodes: dict[str, Node], owner: str) -> str:
    return nodes[owner].kind if owner in nodes else "unknown"


def _render_map(graph: Graph, root: Path, label: str) -> tuple[str, dict[str, str]]:
    nodes = graph.nodes
    feats = sorted(k for k, n in nodes.items() if n.kind == "feat")
    epics = sorted(k for k, n in nodes.items() if n.kind == "epic")
    member: dict[str, list[str]] = {}
    for e in graph.edges:
        if (
            e.rel == "member_of"
            and e.dst in nodes
            and e.src in nodes
            and nodes[e.src].kind == "feat"
        ):
            member.setdefault(e.dst, []).append(e.src)
    parented = {f for kids in member.values() for f in kids}
    n_ac: dict[str, int] = {}
    n_task: dict[str, int] = {}
    jira = {e.src: e.dst[5:] for e in graph.edges if e.rel == "published_as"}
    open_q = {feat: len(qs) for feat, qs in open_questions(graph).items()}
    for e in graph.edges:
        if e.rel == "has_ac" and nodes.get(e.dst) and nodes[e.dst].status != "withdrawn":
            n_ac[e.src] = n_ac.get(e.src, 0) + 1
        if e.rel == "has_task" and nodes.get(e.dst) and nodes[e.dst].status != "withdrawn":
            n_task[e.src] = n_task.get(e.src, 0) + 1

    def feat_line(f: str) -> str:
        n = nodes[f]
        return (
            f"- {md_escape(f)} [{md_escape(n.status)}] {md_escape(n.title)} — "
            f"station {md_escape(n.extra.get('lifecycle', {}).get('station', 'unknown'))} "
            f"({md_escape(n.extra.get('lifecycle', {}).get('condition', 'unknown'))}) · "
            f"Jira {md_escape(jira.get(f, 'UNKNOWN'))} · {n_ac.get(f, 0)} AC · "
            f"{n_task.get(f, 0)} tasks · {open_q.get(f, 0)} open Q"
        )

    pages: dict[str, str] = {}
    for epic in epics:
        n = nodes[epic]
        lines = [
            f"# {md_escape(epic)} {md_escape(n.title)}",
            "",
            f"> {BANNER}",
            "",
            f"Status: {md_escape(n.status)} · "
            f"Scopes: {md_escape(', '.join(n.extra.get('scopes', [])))}",
            "",
        ]
        lines += [feat_line(f) for f in sorted(member.get(epic, []))] or [
            "None — no FEAT is linked."
        ]
        pages[f"maps/{_safe(epic)}.md"] = "\n".join(lines) + "\n"
    layout = workspace.layout_of(root)
    out = [
        f"# Knowledge map — {md_escape(label)}",
        "",
        f"> {BANNER}. Read with the query tool; do not parse by hand.",
        "",
        f"Layout: {layout} · Spec root: . · Epics: {len(epics)} · FEATs: {len(feats)}",
        "",
    ]
    tree: list[str] = []
    for epic in epics:
        n = nodes[epic]
        kids = sorted(member.get(epic, []))
        done = sum(1 for f in kids if nodes[f].status in ("published", "ready-for-dev"))
        tree.append(f"## {md_escape(epic)} [{md_escape(n.status)}] {md_escape(n.title)}")
        tree.append(f"{len(kids)} FEAT · {done} published")
        tree += [feat_line(f) for f in kids]
        tree.append("")
    loose = [f for f in feats if f not in parented]
    if loose:
        tree.append("## Unparented")
        tree += [feat_line(f) for f in loose[:UNPARENTED_CAP]]
        if len(loose) > UNPARENTED_CAP:
            tree.append(f"+{len(loose) - UNPARENTED_CAP} more, run: graph.py find --kind feat")
        tree.append("")
    if len(out) + len(tree) > MAP_LINE_LIMIT - 20:
        tree = []
        for epic in epics:
            kids = member.get(epic, [])
            tree.append(
                f"- {md_escape(epic)} {md_escape(nodes[epic].title)}: {len(kids)} FEAT — "
                f"see maps/{_safe(epic)}.md"
            )
        if loose:
            tree.append(f"- Unparented: {len(loose)} FEAT, run: graph.py find --kind feat")
        tree.append("")
    out += tree or ["No epics or features yet.", ""]
    kinds: dict[str, int] = {}
    for n in nodes.values():
        kinds[n.kind] = kinds.get(n.kind, 0) + 1
    out += ["## Node counts", "", "| Kind | Count |", "|---|---|"]
    out += [f"| {k} | {kinds[k]} |" for k in sorted(kinds)]
    out += [
        "",
        "## How to query",
        "",
        "- graph.py show ID — one node with link counts",
        "- graph.py neighbors ID — paged links with file and line",
        "- graph.py context ID — files to read for an item",
        "- graph.py impact ID — what a change reaches",
        "- graph.py find TEXT --kind K — filter the index",
        "",
    ]
    return "\n".join(out), pages


# ---- writing ---------------------------------------------------------------------------------


def _write_tree(outdir: Path, files: dict[str, str]) -> list[Path]:
    changed: list[Path] = []
    for rel, text in sorted(files.items()):
        path = outdir / rel
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            fsio.atomic_write(path, text)
            changed.append(path)
    for folder in ("shards", "maps"):
        for path in sorted((outdir / folder).rglob("*")) if (outdir / folder).is_dir() else []:
            if path.is_file() and path.relative_to(outdir).as_posix() not in files:
                path.unlink()
    return changed


def graph_dir(root: Path, scope: str | None) -> Path:
    base = root if scope is None else workspace.scope_dir(root, scope)
    return base / schema.GRAPH_DIR


def _emit(root: Path, scopes: list[str], known: list[str], outdir: Path, label: str) -> list[Path]:
    graph = build_graph(root, scopes, known)
    files = _render_files(graph, root, label, scopes)
    inputs = input_files(root, known)
    manifest = {
        "schema_version": schema.GRAPH_SCHEMA_VERSION,
        "label": label,
        "scopes": scopes,
        "layout": workspace.layout_of(root),
        "inputs_digest": digest(root, inputs),
        "inputs": dict(sorted(graph.inputs.items())),
        "files": {
            name: hashing.text_hash(files[name])
            for name in ("index.tsv", "edges-out.tsv", "edges-in.tsv", "KNOWLEDGE-MAP.md")
        },
        "counts": {"nodes": len(graph.nodes), "edges": len(graph.edges)},
    }
    from kitlib import index  # imported here because the index reads graph types

    meta = index.render(graph, root, scopes, label)
    manifest["meta_files"] = {name: hashing.text_hash(text) for name, text in sorted(meta.items())}
    files["manifest.json"] = json.dumps(manifest, indent=1, sort_keys=True) + "\n"
    return _write_tree(outdir, files) + _write_meta(outdir.parent, meta)


def _write_meta(folder: Path, files: dict[str, str]) -> list[Path]:
    """Write the generated index files next to the graph, only when their text changed."""
    changed = []
    for name, text in sorted(files.items()):
        path = folder / name
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            fsio.atomic_write(path, text)
            changed.append(path)
    return changed


def build(root: Path, scope: str | None = None) -> list[Path]:
    """Rebuild one scope's graph, or all of them; a program also gets the merged graph."""
    root = root.resolve()
    all_scopes = workspace.list_scopes(root)
    targets = [scope] if scope else all_scopes
    changed: list[Path] = []
    for item in targets:
        label = item
        changed += _emit(root, [item], [item], graph_dir(root, item), label)
    if workspace.mode_of(root) == "program":
        changed += _emit(root, all_scopes, all_scopes, graph_dir(root, None), "program")
    return changed


def drift_warnings(root: Path, scope: str | None = None) -> list[str]:
    """Files changed outside a logged write, and folders the kit does not know, per scope."""
    from kitlib import writelog

    root = root.resolve()
    scopes = [scope] if scope else workspace.list_scopes(root)
    out = []
    for item in scopes:
        log = workspace.scope_dir(root, item) / "_meta/write-log.md"
        out += [f"{item}: {line}" for line in writelog.drift(log)]
    out += [f for f in build_graph(root, scopes_for(root, scope)).findings if "stray folder" in f]
    return out


def scopes_for(root: Path, scope: str | None) -> list[str]:
    return [scope] if scope else workspace.list_scopes(root)


def check(root: Path, scope: str | None = None) -> list[str]:
    """Drift and link problems; mentioned-only links are notes, not failures."""
    root = root.resolve()
    findings: list[str] = []
    scopes = [scope] if scope else workspace.list_scopes(root)
    for item in scopes:
        outdir = graph_dir(root, item)
        manifest = outdir / "manifest.json"
        if not manifest.is_file():
            findings.append(f"{item}: graph missing; run build")
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("inputs_digest") != digest(root, input_files(root, [item])):
            findings.append(f"{item}: graph is stale; run build")
        for name, recorded in sorted((data.get("meta_files") or {}).items()):
            path = outdir.parent / name
            if not path.is_file():
                findings.append(f"{item}: _meta/{name} is missing; run build")
            elif hashing.text_hash(path.read_text(encoding="utf-8")) != recorded:
                findings.append(f"{item}: _meta/{name} was edited by hand; run build")
        graph = build_graph(root, [item])
        for e in graph.edges:
            if e.res in ("unresolved", "missing", "unsafe-path") and e.cls != "mentioned":
                findings.append(f"{e.src} -{e.rel}-> {e.dst} {e.res} ({e.file}:{e.line})")
            if (
                e.res == "withdrawn"
                and e.cls != "mentioned"
                and e.rel not in ("has_ac", "has_task")
            ):
                findings.append(
                    f"{e.src} -{e.rel}-> {e.dst} references a tombstone ({e.file}:{e.line})"
                )
        jira: dict[str, str] = {}
        for e in graph.edges:
            if e.rel == "published_as" and ":FEAT-" in e.src:
                if e.dst in jira and jira[e.dst] != e.src:
                    findings.append(f"{e.src} duplicate Jira key {e.dst[5:]} with {jira[e.dst]}")
                jira[e.dst] = e.src
        for node in graph.nodes.values():
            state = node.extra.get("lifecycle", {})
            if state.get("condition") == "unknown":
                findings.extend(f"{node.key}: {reason}" for reason in state.get("blockers", []))
        findings += [
            f
            for f in graph.findings
            if "duplicate" in f
            or "not valid JSON" in f
            or "invalid accepted split" in f
            or "stray folder" in f
        ]
    return sorted(set(findings))
