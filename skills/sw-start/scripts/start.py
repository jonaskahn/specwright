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
_shared = _source_shared if _source_shared.is_dir() else _local_shared
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

import argparse
import json

from kitlib import frontmatter, graph_query, workspace  # noqa: E402

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
        n
        for s, n in _status_counts(base / "records", "Q-*.md").items()
        if s in ("candidate", "open")
    )
    freshness = graph_query.Store(root, scope).freshness()
    return {
        "scope": scope,
        "sources": sources,
        "ideas": _status_counts(base / "01-analysis/ideas", "*.md"),
        "feats": feats,
        "feat_ids": drafts,
        "with_tasks": sorted(tasks),
        "open_questions": open_q,
        "graph": freshness,
        "output_default": workspace.output_default(root, scope),
    }


def route(state):
    """Deterministic next action for one scope; each answer carries the evidence behind it."""
    feats, ideas = state["feats"], state["ideas"]
    needs_tasks = [f for f in state["feat_ids"] if f not in state["with_tasks"]]
    if state["graph"] == "missing":
        return (
            "sw-start workspace upgrade, then shared graph build",
            "the knowledge graph is missing",
        )
    if feats.get("draft") or feats.get("in-review"):
        return ("shared lint, then sw-review", "feature drafts are not yet approved")
    if feats.get("ready-to-publish"):
        return (
            "delivery-target prompt, then sw-publish",
            "a reviewed feature is ready to publish; output default is " + state["output_default"],
        )
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


def report(cwd):
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
        item["next"] = list(route(item))
    return {**info, "fresh_setup": False, "scopes_state": scopes}


def hook_lines(data):
    if data.get("fresh_setup"):
        return []
    lines = [f"Specwright: {data['layout']} workspace at {data['spec_root']} ({data['mode']})"]
    for item in data["scopes_state"][:5]:
        feats = ", ".join(f"{n} {s}" for s, n in sorted(item["feats"].items())) or "no features"
        lines.append(f"- {item['scope']}: {feats}; graph {item['graph']}; next: {item['next'][0]}")
    lines.append("Run /sw-start to continue.")
    return lines[:10]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--hook", action="store_true", help="short session summary")
    args = parser.parse_args(argv)
    try:
        data = report(Path(args.cwd).resolve())
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
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        if args.hook:
            return 0
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
