"""Read-only, paged queries over a built graph.

Nothing here loads a whole graph file into memory for a lookup: the index and edge files are
streamed, a node card opens one shard, and every list is paged.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from kitlib import graph, hashing, ids, schema, workspace
from pathlib import Path

DEFAULT_LIMIT = 20
MAX_LIMIT = 200
UP_RELATIONS = {("has_ac", "in"), ("has_task", "in"), ("member_of", "out"), ("realizes", "out")}
DOWN_RELATIONS = {("has_ac", "out"), ("has_task", "out"), ("member_of", "in")}


class QueryError(Exception):
    """The request cannot be answered safely; exit_code tells the caller why."""

    def __init__(self, message: str, code: int = 2, options: list[str] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.options = options or []


class Store:
    def __init__(self, root: Path, scope: str | None) -> None:
        self.root = root.resolve()
        self.scope = scope
        self.dir = graph.graph_dir(self.root, scope)
        self.scopes = [scope] if scope else workspace.list_scopes(self.root)

    def freshness(self) -> str:
        manifest = self.dir / "manifest.json"
        if not manifest.is_file():
            return "missing"
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            current = {
                graph._rel(p, self.root): p.stat().st_size
                for p in graph.input_files(self.root, self.scopes)
            }
        except (OSError, ValueError):
            return "missing"
        return "fresh" if current == data.get("inputs") else "stale"

    def _rows(self, name: str) -> Iterator[list[str]]:
        path = self.dir / name
        if not path.is_file():
            return
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("#"):
                    continue
                yield line.rstrip("\n").split("\t")

    def nodes(self) -> Iterator[dict[str, str]]:
        for r in self._rows("index.tsv"):
            if len(r) >= 6:
                yield dict(zip(("key", "kind", "status", "title", "shard", "loc"), r, strict=False))

    def node(self, key: str) -> dict[str, str] | None:
        for n in self.nodes():
            if n["key"] == key:
                return n
        return None

    def edges(self, direction: str = "out") -> Iterator[graph.Edge]:
        name = "edges-out.tsv" if direction == "out" else "edges-in.tsv"
        for r in self._rows(name):
            if len(r) >= 7:
                yield graph.Edge(r[0], r[1], r[2], r[3], r[4], int(r[5] or 0), r[6])

    def edges_for(self, keys: set[str], direction: str) -> list[graph.Edge]:
        """One pass over the sorted edge file for several keys at once."""
        field = "src" if direction == "out" else "dst"
        return [e for e in self.edges(direction) if getattr(e, field) in keys]

    def shard(self, node: dict[str, str]) -> dict:
        if node["shard"] == "-":
            return {}
        return json.loads((self.dir / node["shard"]).read_text(encoding="utf-8"))

    def resolve(self, text: str) -> str:
        """Qualified key for an ID; STORY aliases map to FEAT; ambiguity is never guessed."""
        text = ids.story_alias(text.strip())
        if text.startswith(("jira:", "code:")) or "/" in text:
            return text
        ref = ids.parse_ref(text)
        if ref is None:
            raise QueryError(f"not a spec ID: {text}", 2)
        if ref.scope:
            return ref.qualified
        hits = sorted(n["key"] for n in self.nodes() if n["key"].split(":", 1)[-1] == ref.id)
        if not hits:
            raise QueryError(f"unknown ID: {text}", 3)
        if len(hits) > 1:
            raise QueryError(f"{text} exists in several scopes; qualify it", 3, hits)
        return hits[0]


def page(rows: Iterator[str], offset: int, limit: int) -> list[str]:
    limit = max(1, min(limit, MAX_LIMIT))
    out: list[str] = []
    skipped = 0
    extra = 0
    for row in rows:
        if skipped < offset:
            skipped += 1
        elif len(out) < limit:
            out.append(row)
        else:
            extra += 1
    if extra:
        out.append(f"+{extra} more (use --offset {offset + limit})")
    return out


def header(store: Store) -> str:
    return f"graph: {store.freshness()}"


def show(store: Store, key: str) -> list[str]:
    node = store.node(key)
    if node is None:
        raise QueryError(f"unknown ID: {key}", 3)
    owner_key = key
    shard = store.shard(node)
    if not shard and node["shard"] == "-":
        owner = next((n for n in store.nodes() if n["key"] == key), None)
        shard = {}
        _ = owner
    lines = [
        f"{key} [{node['kind']}] status={node['status']}",
        f"title: {node['title']}",
        f"at: {node['loc']}",
    ]
    if shard:
        lines.append(f"hash: {shard.get('hash', '-')}  jira: {shard.get('jira', 'UNKNOWN')}")
        lines.append(
            "out: " + (", ".join(f"{k}={v}" for k, v in shard["edges_out"].items()) or "none")
        )
        lines.append(
            "in: " + (", ".join(f"{k}={v}" for k, v in shard["edges_in"].items()) or "none")
        )
    else:
        out_n: dict[str, int] = {}
        for e in store.edges_for({owner_key}, "out"):
            out_n[e.rel] = out_n.get(e.rel, 0) + 1
        in_n: dict[str, int] = {}
        for e in store.edges_for({owner_key}, "in"):
            in_n[e.rel] = in_n.get(e.rel, 0) + 1
        lines.append("out: " + (", ".join(f"{k}={v}" for k, v in sorted(out_n.items())) or "none"))
        lines.append("in: " + (", ".join(f"{k}={v}" for k, v in sorted(in_n.items())) or "none"))
    chain = _chain(store, key)
    if chain:
        lines.append("up: " + " > ".join(chain))
    return lines


def _chain(store: Store, key: str) -> list[str]:
    chain: list[str] = []
    current = key
    seen = {key}
    while True:
        nxt = None
        for e in store.edges_for({current}, "in"):
            if e.rel in ("has_ac", "has_task") and e.src not in seen:
                nxt = e.src
        if nxt is None:
            for e in store.edges_for({current}, "out"):
                if e.rel == "member_of" and e.res == "resolved" and e.dst not in seen:
                    nxt = e.dst
        if nxt is None:
            return chain
        chain.append(nxt)
        seen.add(nxt)
        current = nxt


def neighbors(
        store: Store,
        key: str,
        direction: str,
        rel: str | None,
        declared_only: bool,
        offset: int,
        limit: int,
) -> list[str]:
    if store.node(key) is None and not key.startswith(("jira:", "code:")):
        raise QueryError(f"unknown ID: {key}", 3)
    sides = ["out", "in"] if direction == "both" else [direction]

    def rows() -> Iterator[str]:
        for side in sides:
            for e in store.edges_for({key}, side):
                if rel and e.rel != rel:
                    continue
                if declared_only and e.cls == "mentioned":
                    continue
                arrow = f"-{e.rel}->" if side == "out" else f"<-{e.rel}-"
                other = e.dst if side == "out" else e.src
                yield f"{arrow} {other} [{e.cls}/{e.res}] {e.file}:{e.line}"

    return page(rows(), offset, limit)


def _walk(
        store: Store, key: str, allowed: set[tuple[str, str]], depth: int
) -> Iterator[tuple[int, str, str]]:
    seen = {key}
    frontier = {key}
    for level in range(1, depth + 1):
        found: dict[str, str] = {}
        for side in ("out", "in"):
            for e in store.edges_for(frontier, side):
                if (e.rel, side) not in allowed:
                    continue
                other = e.dst if side == "out" else e.src
                if other not in seen:
                    found.setdefault(other, e.rel)
        if not found:
            return
        for other in sorted(found):
            seen.add(other)
            yield level, other, found[other]
        frontier = set(found)


def up(store: Store, key: str, offset: int, limit: int) -> list[str]:
    store_check(store, key)
    rows = (f"{'  ' * (lvl - 1)}{k} ({r})" for lvl, k, r in _walk(store, key, UP_RELATIONS, 6))
    return page(rows, offset, limit)


def down(store: Store, key: str, depth: int, offset: int, limit: int) -> list[str]:
    store_check(store, key)
    rows = (
        f"{'  ' * (lvl - 1)}{k} ({r})" for lvl, k, r in _walk(store, key, DOWN_RELATIONS, depth)
    )
    return page(rows, offset, limit)


def store_check(store: Store, key: str) -> None:
    if store.node(key) is None:
        raise QueryError(f"unknown ID: {key}", 3)


def path(store: Store, a: str, b: str, longest: int) -> list[str]:
    store_check(store, a)
    store_check(store, b)
    parent: dict[str, tuple[str, graph.Edge, str]] = {}
    seen = {a}
    frontier = {a}
    for _ in range(longest):
        step: dict[str, tuple[str, graph.Edge, str]] = {}
        for side in ("out", "in"):
            for e in store.edges_for(frontier, side):
                here, other = (e.src, e.dst) if side == "out" else (e.dst, e.src)
                if other not in seen and other not in step:
                    step[other] = (here, e, side)
        for other, value in step.items():
            parent[other] = value
        seen |= set(step)
        frontier = set(step)
        if b in seen or not frontier:
            break
    if b not in parent and a != b:
        return [f"no connection within {longest} hops"]
    hops: list[str] = []
    cur = b
    while cur != a:
        prev, e, side = parent[cur]
        arrow = f"-{e.rel}->" if side == "out" else f"<-{e.rel}-"
        hops.append(f"{prev} {arrow} {cur} [{e.cls}/{e.res}] {e.file}:{e.line}")
        cur = prev
    return list(reversed(hops)) or [f"{a} is {b}"]


def impact(store: Store, target: str, include_mentions: bool = False) -> dict[str, list[str]]:
    if target.startswith("jira:"):
        seeds = {e.src for e in store.edges_for({target}, "in") if e.rel == "published_as"}
        if not seeds:
            raise QueryError(f"unknown Jira key: {target[5:]}", 3)
    else:
        store_check(store, target)
        seeds = {target}
    reached = set(seeds)
    while True:
        added: set[str] = set()
        for e in store.edges_for(reached, "in"):
            if e.rel == "mentions" and not include_mentions:
                continue
            if e.rel in ("published_as", "last_snapshot"):
                continue
            added.add(e.src)
        for e in store.edges_for(reached, "out"):
            if e.rel in ("has_ac", "has_task"):
                added.add(e.dst)
        added -= reached
        if not added:
            break
        reached |= added
    jira = sorted(e.dst[5:] for e in store.edges_for(reached, "out") if e.rel == "published_as")
    pick = lambda marker: sorted(k for k in reached if marker in k)  # noqa: E731
    return {
        "features": pick(":FEAT-"),
        "criteria": pick(":AC-"),
        "tasks": pick(":TASK-"),
        "jira": jira,
    }


def find(
        store: Store,
        text: str | None,
        kind: str | None,
        status: str | None,
        jira: str | None,
        epic: str | None,
        offset: int,
        limit: int,
) -> list[str]:
    allowed: set[str] | None = None
    if jira:
        allowed = {
            e.src for e in store.edges_for({f"jira:{jira}"}, "in") if e.rel == "published_as"
        }
    if epic:
        epic_key = store.resolve(epic)
        members = {e.src for e in store.edges_for({epic_key}, "in") if e.rel == "member_of"}
        allowed = members if allowed is None else allowed & members
    needle = (text or "").lower()

    def rows() -> Iterator[str]:
        for n in store.nodes():
            if kind and n["kind"] != kind:
                continue
            if status and n["status"] != status:
                continue
            if allowed is not None and n["key"] not in allowed:
                continue
            if needle and needle not in (n["key"] + " " + n["title"]).lower():
                continue
            yield f"{n['key']} [{n['kind']}] {n['status']} {n['title']} @ {n['loc']}"

    return page(rows(), offset, limit)


def current_hash(path_text: str, root: Path) -> str:
    target = root / path_text
    if path_text.endswith(".json"):
        return hashing.bytes_hash(target.read_bytes())
    text = target.read_text(encoding="utf-8")
    return hashing.text_hash(text) if path_text.endswith(".feature") else hashing.draft_hash(text)


def context(store: Store, key: str, with_text: bool, budget: int) -> list[str]:
    store_check(store, key)
    focus = key
    for e in store.edges_for({key}, "in"):
        if e.rel in ("has_ac", "has_task"):
            focus = e.src
    items: list[tuple[str, str]] = []  # role, key
    items.append(("self", key))
    if focus != key:
        items.append(("story", focus))
    related: dict[str, str] = {}
    children = {e.dst for e in store.edges_for({focus}, "out") if e.rel in ("has_ac", "has_task")}
    for e in store.edges_for({focus}, "out"):
        role = {
            "realizes": "objective",
            "governed_by": "rule",
            "shaped_from": "idea",
            "sourced_from": "source",
            "last_snapshot": "snapshot",
            "touches": "code",
            "member_of": "epic",
        }.get(e.rel)
        if role:
            related.setdefault(e.dst, role)
    for e in store.edges_for({focus, *children}, "in"):
        role = {
            "derives_from": "artifact",
            "illustrates": "diagram",
            "affects": "record",
            "exercises": "scenario",
        }.get(e.rel)
        if role and e.res != "unresolved":
            related.setdefault(e.src, role)
    for e in store.edges_for({focus, *children}, "out"):
        if e.rel == "touches":
            related.setdefault(e.dst, "code")
    for k, role in sorted(related.items(), key=lambda kv: (kv[1], kv[0])):
        items.append((role, k))
    lines: list[str] = []
    used = 0
    for role, k in items:
        node = store.node(k)
        if node is None:
            lines.append(f"{role}: {k} UNRESOLVED")
            continue
        span = node["loc"]
        shard_node = node
        info = store.shard(shard_node) if node["shard"] != "-" else {}
        lines.append(f"{role}: {k} {span} hash={info.get('hash', '-')}")
        if not with_text or node["loc"] == "-" or node["kind"] in ("code", "jira"):
            continue
        file_part = node["loc"].rsplit(":", 1)[0]
        want = info.get("hash", "-")
        if want == "-":
            owner = store.node(focus)
            want = store.shard(owner).get("hash", "-") if owner else "-"
        try:
            actual = current_hash(file_part, store.root)
        except OSError:
            lines.append("  STALE: file unreadable; text omitted")
            continue
        if want != "-" and actual != want:
            lines.append("  STALE: file changed since build; text omitted")
            continue
        start = int(node["loc"].rsplit(":", 1)[1] or 1)
        end = int(info.get("end", 0) or 0) or start + 40
        slice_ = (
            (store.root / file_part)
            .read_text(encoding="utf-8")
            .splitlines()[max(0, start - 1): end]
        )
        chunk = "\n".join("  | " + s for s in slice_)
        if used + len(chunk) > budget:
            lines.append("  (budget reached; text omitted)")
            break
        used += len(chunk)
        lines.append(chunk)
    return lines


def stats(store: Store) -> list[str]:
    kinds: dict[str, int] = {}
    for n in store.nodes():
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    classes: dict[str, int] = {}
    for e in store.edges("out"):
        classes[e.cls] = classes.get(e.cls, 0) + 1
    return [
        "nodes: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())),
        "edges: " + ", ".join(f"{k}={v}" for k, v in sorted(classes.items())),
    ]


def read_map(store: Store, epic: str | None) -> str:
    if epic:
        key = store.resolve(epic)
        page_path = store.dir / "maps" / f"{graph._safe(key)}.md"
    else:
        page_path = store.dir / "KNOWLEDGE-MAP.md"
    if not page_path.is_file():
        raise QueryError("no map yet; run build", 3)
    return page_path.read_text(encoding="utf-8")


_ = schema
