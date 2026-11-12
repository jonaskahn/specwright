#!/usr/bin/env python3
"""Report where a Specwright workspace stands and which skill comes next. Read-only.

Exit codes: 0 report produced, 2 usage or unreadable workspace, 3 a choice is required
(for example two spec roots in one folder). With --hook it prints at most ten lines, and
nothing at all when no spec root is found.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

import argparse
import json

from kitlib import (  # noqa: E402
    baseline,
    frontmatter,
    graph_query,
    guard,
    hashing,
    index,
    invest,
    schema,
    workspace,
)

CODE_MARKERS = (
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "src",
    "app",
    "lib",
)


def _status_counts(folder, pattern):
    counts = {}
    for path in sorted(folder.glob(pattern)) if folder.is_dir() else []:
        if path.is_symlink() or path.name.endswith(".card.md"):
            continue
        parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
        status = str((parsed.fm or {}).get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def baseline_state(root, scope, base, store, fresh):
    """Where an existing-baseline start stands: sources, snapshots and the legacy register."""
    sources = workspace.source_list(root, scope)
    snapshots = [p for p in (base / "00-inbox").glob("SRC-*.md") if not p.is_symlink()]
    register = index.read_register(base / baseline.REGISTER)
    mapped = set()
    if fresh:
        for node in store.nodes():
            if node["kind"] == "feat":
                mapped |= {a.casefold() for a in node.get("aliases", "").split("|") if a}
    unmapped = [r["legacy_id"] for r in register or [] if r["legacy_id"].casefold() not in mapped]
    return {
        "sources_registered": len(sources),
        "snapshots": len(snapshots),
        "register_items": len(register) if register is not None else None,
        "legacy_unmapped": len(unmapped),
    }


def baseline_step(state):
    """(skill, evidence, action) for the next existing-baseline step, or None.

    The flow applies while imported or registered sources exist but nothing has been shaped yet.
    """
    b = state["baseline"]
    started = b["sources_registered"] or b["snapshots"]
    if not started or state["ideas"] or state["feats"]:
        return None
    if b["register_items"] is not None:
        return (
            "sw-shape",
            f"a legacy register of {b['register_items']} item(s) is imported and not yet shaped",
            "baseline.py propose-grouping, then reserve and brief for each group",
        )
    if b["snapshots"]:
        return (
            "sw-shape",
            f"{b['snapshots']} snapshot(s) exist and no legacy register is imported",
            "baseline.py import-register <legacy register file> --dry-run",
        )
    return (
        "sw-ingest",
        f"{b['sources_registered']} source(s) are registered and nothing is imported",
        "bulk_import.py --batch-id <id> --list-file <list> --dry-run",
    )


def scope_state(root, scope):
    base = workspace.scope_dir(root, scope)
    raw = base / "00-inbox/raw"
    sources = (
        sum(1 for p in raw.rglob("*") if p.is_file() and p.name != ".gitkeep")
        if raw.is_dir()
        else 0
    )
    plan = base / "03-plan"
    tasks = {p.name.split(".")[0] for p in plan.glob("*.tasks.md")} if plan.is_dir() else set()
    feats = _status_counts(base / "02-drafts", "*.story.md")
    drafts = sorted(p.name.split(".")[0] for p in (base / "02-drafts").glob("*.story.md"))
    open_q = sum(
        n for s, n in _status_counts(base / "records", "Q-*.md").items() if s in schema.OPEN_Q
    )
    store = graph_query.Store(root, scope)
    freshness = store.freshness()
    state_baseline = baseline_state(root, scope, base, store, freshness == "fresh")
    return {
        "baseline": state_baseline,
        "setup": setup_needed(root, scope),
        "scope": scope,
        "sources": sources,
        "ideas": _status_counts(base / "01-analysis/ideas", "*.md"),
        "feats": feats,
        "feat_ids": drafts,
        "with_tasks": sorted(tasks),
        "open_questions": open_q,
        "graph": freshness,
        "output_default": workspace.output_default(root, scope),
        "board": graph_query.board(graph_query.Store(root, scope)) if freshness == "fresh" else [],
    }


def setup_needed(root, scope):
    """What the project still lacks before records can be approved or decided."""
    missing = []
    if not workspace.approver_list(root, scope):
        missing.append(
            "approvers: run workspace.py approvers add --role <role> --name <name> "
            "--account-id <id>"
        )
    return missing


def _depends(base, feat_id):
    """Dependencies of a feature that are not yet published or ready for dev."""
    story = base / "02-drafts" / f"{feat_id}.story.md"
    if not story.is_file():
        return []
    deps = (frontmatter.parse(story.read_text(encoding="utf-8")).fm or {}).get("depends_on") or []
    unmet = []
    for dep in deps:
        path = base / "02-drafts" / f"{dep}.story.md"
        status = (
            (frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}).get("status")
            if path.is_file()
            else None
        )
        if status not in ("published", "ready-for-dev"):
            unmet.append(str(dep))
    return unmet


def rank(root, scope, board, store):
    """Readiness advice for the active features: fewest blockers first. The user chooses."""
    base = workspace.scope_dir(root, scope)
    nodes = [n for n in store.nodes() if n["kind"] == "feat"]
    cells = {}
    for brief in sorted((base / "01-analysis/ideas").glob("*.md")):
        body = frontmatter.parse(brief.read_text(encoding="utf-8")).body
        rows, _ = invest.parse(body) if invest.has_section(body) else ([], [])
        for row in rows:
            label = row["Feature"].casefold()
            for node in nodes:
                names = [node["title"].casefold(), node["key"].split(":")[-1].casefold()]
                names += [a.casefold() for a in node.get("aliases", "").split("|") if a]
                if any(n and n in label for n in names):
                    cells[node["key"]] = invest.row_summary(row)
    ranked = []
    for item in board:
        if item.get("kind") == "epic":
            continue
        key = item["id"]
        feat_id = key.split(":")[-1]
        blocked, asked = item.get("blocked_by_q") or [], item.get("open_q") or []
        summary = cells.get(key, {"fail": 0, "unknown": 0})
        unmet = _depends(base, feat_id)
        score = (
            3 * len(blocked)
            + (len(asked) - len(blocked))
            + 2 * summary["fail"]
            + summary["unknown"]
            + 2 * len(unmet)
        )
        reasons = []
        if blocked:
            reasons.append(f"{len(blocked)} blocking question(s)")
        if len(asked) > len(blocked):
            reasons.append(f"{len(asked) - len(blocked)} other open question(s)")
        if summary["fail"]:
            reasons.append(f"{summary['fail']} failed INVEST cell(s)")
        if summary["unknown"]:
            reasons.append(f"{summary['unknown']} unknown INVEST cell(s), including size")
        if unmet:
            reasons.append("waits on " + ", ".join(unmet))
        ranked.append({"id": key, "score": score, "reasons": reasons or ["no blockers found"]})
    ranked.sort(key=lambda r: (r["score"], r["id"]))
    return ranked[:3]


def route(state):
    """Deterministic next action for one scope; each answer carries the evidence behind it."""
    if state["graph"] in ("missing", "incompatible"):
        return ("sw-start workspace upgrade dry-run", "board schema is missing or incompatible")
    if state["graph"] != "fresh":
        return ("shared graph build", "board is unavailable until the graph is fresh")
    step = baseline_step(state)
    if step:
        return (step[0], "existing baseline: " + step[1])
    board = [
        r for r in state.get("board", []) if r.get("kind") != "epic" or r["condition"] != "complete"
    ]
    if len(board) > 1:
        top = state.get("ranking") or []
        hint = f"; most ready: {top[0]['id']} ({'; '.join(top[0]['reasons'])})" if top else ""
        return ("choose item", "several active features; select a qualified item" + hint)
    if len(board) == 1:
        item = board[0]
        station = item["station"]
        return (
            "sw-" + station if item["condition"] != "unknown" else "shared status",
            f"{item['id']} remains in {station} ({item['condition']})",
        )
    feats, ideas = state["feats"], state["ideas"]
    needs_tasks = [f for f in state["feat_ids"] if f not in state["with_tasks"]]
    if feats.get("draft"):
        return ("sw-spec", "drafts remain in specification")
    if feats.get("in-review"):
        return ("sw-review", "a feature was submitted to review")
    if feats.get("ready-to-publish"):
        return ("sw-plan", "reviewed requirements need a local implementation plan")
    if (feats.get("published") or feats.get("ready-for-dev")) and needs_tasks:
        return ("sw-plan", "approved features have no tasks file: " + ", ".join(needs_tasks))
    if ideas.get("accepted") and not feats:
        return ("sw-spec", "an accepted idea has no feature drafts")
    if ideas.get("draft") and not feats:
        return ("sw-shape", "an idea is still a draft")
    if not state["sources"] and not ideas and not feats:
        return ("sw-ingest", "the project has no sources, ideas or features")
    return ("shared status", "no single next step is evident; read the full report")


def default_layout(cwd):
    here = Path(cwd).resolve()
    has_code = any((here / m).exists() for m in CODE_MARKERS)
    return "embedded" if has_code and (here / ".git").exists() else "docs"


ROLE_ORDER = ("manifest", "read-first", "item", "parent", "source", "decision", "amendment")


def context_pack(root, scope, key, store, board_row):
    """Files to read for one item, in reading order, with hashes and its blocking questions."""
    if store.freshness() != "fresh":
        raise graph_query.QueryError(
            "the graph must be fresh for a context pack; run graph build", 3
        )
    base = workspace.scope_dir(root, scope)
    rows = {r["key"]: r for r in graph_query.meta_rows(store, "index.tsv")}
    if key not in rows:
        raise graph_query.QueryError(f"{key} is not in the master index; run graph build", 3)
    files = []

    def add(role, name, path, digest):
        files.append({"role": role, "name": name, "path": path, "hash": digest})

    manifest = base / workspace.FLAT_MANIFEST
    add(
        "manifest",
        "project manifest",
        str(manifest.relative_to(root)),
        hashing.bytes_hash(manifest.read_bytes())[:12],
    )
    first = base / "_meta/READ-FIRST.md"
    if first.is_file():
        add(
            "read-first",
            "read-first list",
            str(first.relative_to(root)),
            hashing.bytes_hash(first.read_bytes())[:12],
        )
    row = rows[key]
    add("item", row["name"] or key, row["path"].rsplit(":", 1)[0], row["hash"])
    if row.get("parent") in rows:
        parent = rows[row["parent"]]
        add(
            "parent",
            parent["name"] or parent["key"],
            parent["path"].rsplit(":", 1)[0],
            parent["hash"],
        )
    blocking = set(board_row.get("blocked_by_q") or []) if board_row else set()
    questions = []
    for link in filter(None, row["links"].split(",")):
        rel, _, other = link.lstrip("~").partition(":")
        target = rows.get(other)
        if target is None:
            continue
        kind = target["kind"]
        role = {"snapshot": "source", "dec": "decision", "amendment": "amendment"}.get(kind)
        if kind == "q":
            questions.append(
                {
                    "key": other,
                    "title": target["name"],
                    "blocking": other in blocking,
                    "status": target["status"].split(",")[0],
                }
            )
        elif role and target["path"] != "-":
            add(role, target["name"] or other, target["path"].rsplit(":", 1)[0], target["hash"])
    files.sort(key=lambda f: ROLE_ORDER.index(f["role"]))
    return {
        "item": key,
        "files": files,
        "questions": sorted(questions, key=lambda q: (not q["blocking"], q["key"])),
    }


def action_for(item):
    """One concrete next action in plain words; the user decides whether to take it."""
    if item.get("setup"):
        return item["setup"][0]
    skill, reason = item["next"][0], item["next"][1]
    if reason.startswith("existing baseline"):
        return baseline_step(item)[2]
    active = [r for r in item.get("board", []) if r.get("kind") != "epic"]
    if skill == "choose item":
        top = (item.get("ranking") or [{"id": "REF:FEAT-001"}])[0]["id"]
        return f"name the item to work on, for example {top}; the ranking is advice"
    if len(active) == 1:
        return f"run {skill} on {active[0]['id']}"
    return f"run {skill}"


def report(cwd, target=None, pack=False):
    info = workspace.detect(cwd)
    if info["mode"] == "none":
        return {
            **info,
            "fresh_setup": True,
            "suggested_layout": default_layout(cwd),
            "next": ["sw-start", "choose a layout and then ingest, shape or supply a baseline"],
            "scopes_state": [],
        }
    root = Path(info["spec_root"])
    scopes = [scope_state(root, s) for s in info["scopes"]]
    for item in scopes:
        if item["graph"] == "fresh":
            item["ranking"] = rank(
                root, item["scope"], item["board"], graph_query.Store(root, item["scope"])
            )
    if target:
        store = graph_query.Store(
            root, None if workspace.mode_of(root) == "program" else scopes[0]["scope"]
        )
        selected = store.resolve(target)
        scopes = [s for s in scopes if s["scope"] == selected.split(":")[0]]
        if not scopes or store.node(selected) is None:
            raise graph_query.QueryError(f"unknown item: {selected}", 3)
        scopes[0]["board"] = graph_query.board(
            graph_query.Store(root, scopes[0]["scope"]), selected
        )
        if pack:
            row = next((r for r in scopes[0]["board"] if r["id"] == selected), None)
            scopes[0]["pack"] = context_pack(
                root, scopes[0]["scope"], selected, graph_query.Store(root, scopes[0]["scope"]), row
            )
        if ":EPIC-" in selected:
            scopes[0]["next"] = [
                "choose item",
                "named epic; select a feature slice or request shaping",
            ]
            return {**info, "fresh_setup": False, "scopes_state": scopes}
    for item in scopes:
        item["next"] = list(route(item))
        item["action"] = action_for(item)
    return {**info, "fresh_setup": False, "scopes_state": scopes}


def hook_lines(data):
    if data.get("fresh_setup"):
        return []
    lines = [
        f"Specwright {data['kit_version']}: {data['layout']} workspace at "
        f"{data['spec_root']} ({data['mode']})"
    ]
    for item in data["scopes_state"][:5]:
        feats = ", ".join(f"{n} {s}" for s, n in sorted(item["feats"].items())) or "no features"
        lines.append(f"- {item['scope']}: {feats}; graph {item['graph']}; next: {item['next'][0]}")
    lines.append("Run /sw-start to continue.")
    return lines[:10]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--item", help="qualified epic or feature to resume")
    parser.add_argument("--pack", action="store_true", help="with --item: files to read, in order")
    parser.add_argument("--hook", action="store_true", help="short session summary")
    args = parser.parse_args(argv)
    problems = guard.check(_here.parent)
    if problems:
        print(guard.explain(problems), file=sys.stderr if not args.hook else sys.stdout)
        return 0 if args.hook else 2
    try:
        data = {
            "kit_version": schema.KIT_VERSION,
            **report(Path(args.cwd).resolve(), args.item, args.pack),
        }
        if args.hook:
            print("\n".join(hook_lines(data)))
            return 0
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    except workspace.AskUser as ask:
        if args.hook:
            return 0
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except graph_query.QueryError as exc:
        if args.hook:
            return 0
        print(f"error: {exc}", file=sys.stderr)
        return exc.code
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        if args.hook:
            return 0
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
