#!/usr/bin/env python3
"""Write one self-contained prompt per task for an implementing agent (Claude Code or similar).

    task_prompts.py --feat FEAT-NNN [--scope SCOPE] [--cwd <project>] [--draft]

Output: 03-plan/prompts/FEAT-NNN/TASK-NNN-n.md plus _order.md (dependency order). Each prompt
holds the task, its acceptance criteria verbatim, the rule lines it traces to, the locked stack
for its layer, inputs and the stop conditions; nothing else, so an agent needs no other file.
The folder is regenerated each run (prompts of withdrawn tasks are removed). Prompts are
derived: never edit them; change the story or tasks and regenerate.

Exit codes: 0 written, 1 tasks not ready (without --draft) or invalid, 2 usage or file error.
"""

import argparse
import re
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

from kitlib import analysis, frontmatter, fsio, hashing, ids, markdown, stack, workspace  # noqa: E402

OUT = "prompts"


def _order(blocks: dict) -> list[str]:
    """Task IDs in dependency order; ties keep file order. Cycles keep file order too."""
    deps = {
        tid: [r.id for r in ids.find_refs(b.field_line("Depends on")) if r.id in blocks]
        for tid, b in blocks.items()
    }
    done: list[str] = []
    pending = list(blocks)
    while pending:
        ready = [t for t in pending if all(d in done for d in deps[t])]
        if not ready:
            done += pending
            break
        done.append(ready[0])
        pending.remove(ready[0])
    return done


def _existing(base: Path, feat: str, fm: dict, body: str) -> dict:
    """For work on existing code: files to read first, regression tests, must-not-change ACs."""
    target = str(fm.get("changes") or "").split(":")[-1]
    cited = body
    tbody = ""
    if target and (base / "02-drafts" / f"{target}.story.md").is_file():
        tbody = frontmatter.parse(
            (base / "02-drafts" / f"{target}.story.md").read_text(encoding="utf-8")
        ).body
        cited += tbody
    code, tests = [], []
    for a in sorted((base / "01-analysis" / "as-is").glob("*.analysis.md")):
        text = a.read_text(encoding="utf-8")
        afm = frontmatter.parse(text).fm or {}
        rel = a.relative_to(base).as_posix()
        if rel not in cited and str(afm.get("target", "")).split(":")[-1] not in (feat, target):
            continue
        for m in analysis.CODE_CITE.finditer(text):
            path = f"{m.group(1)}/{m.group(2)}"
            bucket = tests if analysis.TEST_PATH.search(m.group(2)) else code
            if path not in bucket:
                bucket.append(path)
    keep = []
    sec = markdown.sections(body, level=3).get("Must not change")
    if sec and tbody:
        tacs = markdown.ac_blocks(markdown.sections(tbody).get("Acceptance criteria"))
        for ac_id in re.findall(r"AC-\d{3}-\d+", sec.text):
            if ac_id in tacs:
                keep.append(f"{ac_id} — {tacs[ac_id].title}")
    return {"read_first": code[:8], "tests": tests[:8], "keep": keep, "target": target}


def _rule_lines(body: str, refs: list[str]) -> list[str]:
    wanted = [r for r in refs if r.startswith(("BR-", "NFR-"))]
    out = []
    for name in ("Business rules", "Non-functional"):
        section = markdown.sections(body).get(name)
        if section is None:
            continue
        for _, line in section.lines:
            if any(r in line for r in wanted) and line.strip() not in out:
                out.append(line.strip())
    return out


def build(base: Path, scope: str, feat: str, draft: bool) -> tuple[list[Path], list[str]]:
    story_path = base / "02-drafts" / f"{feat}.story.md"
    tasks_path = base / "03-plan" / f"{feat}.tasks.md"
    if not story_path.is_file() or not tasks_path.is_file():
        return [], [f"{feat}: story or tasks file missing"]
    story = story_path.read_text(encoding="utf-8")
    tasks_text = tasks_path.read_text(encoding="utf-8")
    sp, tp = frontmatter.parse(story), frontmatter.parse(tasks_text)
    if sp.error or tp.error or not sp.fm or not tp.fm:
        return [], [f"{feat}: invalid front matter"]
    status = str(tp.fm.get("status", "draft"))
    if status != "ready" and not draft:
        return [], [f"{feat}: tasks status is {status}; pass check_tasks.py --mark-ready first"]
    full_hash = hashing.draft_hash(story)
    spec_hash = full_hash[:19]  # sha256:<12>, enough to detect a stale prompt
    if tp.fm.get("spec_hash") != full_hash:
        return [], [f"{feat}: tasks are stale against the story; regenerate tasks first"]
    acs = markdown.ac_blocks(markdown.sections(sp.body).get("Acceptance criteria"))
    blocks = markdown.task_blocks(tp.body)
    profile = stack.effective(_root_of(base), scope)
    lock = (profile or {}).get("locked") or {}
    libs = (profile or {}).get("libraries") or {}
    summary = str(sp.fm.get("jira_summary") or feat)
    folder = base / "03-plan" / OUT / feat
    folder.mkdir(parents=True, exist_ok=True)
    order = _order(blocks)
    existing = _existing(base, feat, sp.fm, sp.body)
    written = []
    for tid in order:
        b = blocks[tid]
        layer = markdown.task_layer(b.title)
        refs = [r.id for r in ids.find_refs(b.field_line("Traces to"))]
        lines = [
            f"# {tid} — {b.title}",
            "",
            f"Feature: {scope}:{feat} — {summary}",
            f"Source: spec_hash {spec_hash} · tasks {status}"
            + (" · DRAFT: do not start" if status != "ready" else ""),
            "",
            "## Goal",
            b.title.split("]", 1)[-1].strip(),
            "",
            "## Done when",
            b.field_line("Done when") or "UNKNOWN",
            "",
            "## Acceptance criteria",
        ]
        for ref in [r for r in refs if r.startswith("AC-")]:
            ac = acs.get(ref)
            lines += (
                [f"### {ref} — {ac.title}", ac.text.strip(), ""]
                if ac
                else [f"- {ref}: UNKNOWN", ""]
            )
        rules = _rule_lines(sp.body, refs)
        lines += ["## Rules", *(rules or ["None"]), ""]
        stack_line = b.field_line("Stack") or stack.layer_line(profile, layer)
        lines += [
            "## Stack" + (f" (locked {lock.get('hash')})" if lock.get("hash") else " (NOT LOCKED)"),
            stack_line or "None — non-code layer",
        ]
        if libs.get("forbidden"):
            lines.append("Forbidden: " + ", ".join(libs["forbidden"]))
        if libs.get("needs_approval"):
            lines.append("Needs approval: " + ", ".join(libs["needs_approval"]))
        for c in (profile or {}).get("conventions") or []:
            lines.append(f"Convention: {c}")
        if existing["read_first"] or existing["tests"] or existing["keep"]:
            lines += ["", "## Existing code"]
            if existing["target"]:
                lines.append(
                    f"Changes {existing['target']}; behaviour not in the Delta stays as is."
                )
            if existing["read_first"]:
                lines.append("Read first: " + "; ".join(existing["read_first"]))
                lines.append("Follow the patterns in these files; do not restructure them.")
            if existing["keep"]:
                lines += ["Must not change:", *(f"- {k}" for k in existing["keep"])]
            if existing["tests"]:
                lines.append("Regression tests (must stay green): " + "; ".join(existing["tests"]))
        lines += ["", "## Inputs"]
        for name in ("Depends on", "Touches", "Visuals"):
            value = b.field_line(name)
            if value:
                lines.append(f"{name}: {value}")
        test = ((profile or {}).get("layers") or {}).get(layer or "", {}).get("test")
        stop_if = (b.field_line("Stop and ask if") or "an AC or rule is unclear").rstrip(".")
        lines += [
            "",
            "## Rules of engagement",
            "- Implement this task only. Do not edit story, plan, tasks or prompt files.",
            "- Use only the stack above. New libraries outside it: stop and ask.",
            f"- Before done: `{test}` passes."
            if test
            else "- Before done: tests for the Done when pass.",
            f"- Stop and ask if: {stop_if}.",
            "- Stop on any conflict between code, criteria and stack. Do not guess.",
            "- Report: files changed, test result, AC IDs satisfied.",
        ]
        target = folder / f"{tid}.md"
        fsio.atomic_write(target, "\n".join(lines).rstrip() + "\n")
        written.append(target)
    keep = {p.name for p in written} | {"_order.md"}
    for old in folder.glob("*.md"):
        if old.name not in keep:
            old.unlink()
    index = [f"# {feat} — task order", "", f"spec_hash {spec_hash}", ""]
    index += [f"{n}. {tid} — {blocks[tid].title}" for n, tid in enumerate(order, 1)]
    fsio.atomic_write(folder / "_order.md", "\n".join(index) + "\n")
    return written, []


def _root_of(base: Path) -> Path:
    root = workspace.find_root(base)
    if root is None:
        raise ValueError("no workspace")
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feat", required=True)
    parser.add_argument("--scope")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--draft", action="store_true", help="also for tasks not yet ready")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, args.feat, cwd, True)
        feat = args.feat.split(":")[-1]
        written, problems = build(workspace.scope_dir(root, scope), scope, feat, args.draft)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        for p in written:
            print(p.relative_to(workspace.scope_dir(root, scope)).as_posix())
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
