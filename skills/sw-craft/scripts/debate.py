#!/usr/bin/env python3
"""Independent review before finalizing: a review pack for the owner, a brief for independent
reviewers, and a check of the debate record.

    debate.py pack  --feat FEAT-NNN    what the owner has not reviewed yet (writes review/…pack.md)
    debate.py brief --feat FEAT-NNN    reviewer brief: roles, files to read, output format
    debate.py start --feat FEAT-NNN    empty debate record bound to the current draft hash
    debate.py seal  --feat FEAT-NNN    after fixes: bind the record to the current hash
    debate.py check --feat FEAT-NNN    validate the record; finalizable or not, open disputes

Common: --cwd <project> [--scope S]. Files go to 02-drafts/review/. Nothing here approves:
only `review.py accept` records the owner's finalize, and it requires a passing check.
Exit codes: 0 ok (check: finalizable), 1 check not finalizable, 2 usage or file error.
"""

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(f"error: shared library missing at {_shared}/kitlib; reinstall this skill")
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, fsio, hashing, markdown, workspace  # noqa: E402

ROLES = ("critic", "builder", "tester")
SEVERITY = ("blocker", "major", "minor")
RESPONSE = ("accepted", "rebutted", "open")
EVIDENCE = re.compile(
    r"(AC-\d{3}-\d+|BR-\d{3}|N?FR-[A-Z]{2,5}-\d{3}|SRC-\d{4}:L\d+|CODE:\S+|Q-\d{3}|L\d+|§)"
)
FOLDER = "02-drafts/review"

ROLE_BRIEF = {
    "critic": "Find ambiguity, contradictions (inside the story, with its sources, with the target "
    "feature for a change), hidden assumptions, missing rules or edge cases, scope creep.",
    "builder": "Act as the developer who must build this alone. List every point where you would "
    "have to guess: undefined data, states, errors, limits, integrations, existing code impact.",
    "tester": "Act as QA. For each AC: can you write one pass and one fail test from text alone? "
    "List untestable criteria, missing negative cases, unmeasurable NFRs, absent test data.",
}


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""


def _paths(base: Path, feat: str) -> dict[str, Path]:
    return {
        "story": base / "02-drafts" / f"{feat}.story.md",
        "card": base / "02-drafts" / f"{feat}.card.md",
        "pack": base / FOLDER / f"{feat}.pack.md",
        "brief": base / FOLDER / f"{feat}.brief.md",
        "debate": base / FOLDER / f"{feat}.debate.md",
    }


def _questions(base: Path, feat: str) -> list[str]:
    out = []
    for path in sorted((base / "records").glob("Q-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        affects = " ".join(str(x) for x in (fm.get("affects") or []))
        if re.search(rf"\b{feat}\b", affects) and fm.get("status") not in ("answered", "withdrawn"):
            default = f"; default applied: {fm.get('default')}" if fm.get("default") else ""
            out.append(f"{fm.get('id')} [{fm.get('status')}] {fm.get('title')}{default}")
    return out


def _analyses(base: Path, feat: str, fm: dict) -> list[str]:
    """Analysis files for this feature: by target, or cited by path in it or its target."""
    target = str(fm.get("changes") or "").split(":")[-1]
    texts = [_paths(base, f)["story"] for f in (feat, target) if f]
    cited = " ".join(t.read_text(encoding="utf-8") for t in texts if t.is_file())
    out = []
    for a in sorted((base / "01-analysis" / "as-is").glob("*.analysis.md")):
        rel = a.relative_to(base).as_posix()
        afm = frontmatter.parse(a.read_text(encoding="utf-8")).fm or {}
        if rel in cited or str(afm.get("target", "")).split(":")[-1] in (feat, target):
            out.append(rel)
    return out


def pack(base: Path, feat: str) -> Path:
    p = _paths(base, feat)
    story = p["story"].read_text(encoding="utf-8")
    fm = frontmatter.parse(story).fm or {}
    digest = hashing.draft_hash(story)
    card = p["card"].read_text(encoding="utf-8") if p["card"].is_file() else ""
    summary = markdown.sections(frontmatter.parse(card).body).get("Summary") if card else None
    rel = p["story"].relative_to(workspace.find_root(base) or base)
    last = _git(base, "log", "-1", "--format=%h", "--grep=^sw-craft", "--", str(p["story"]))
    last = last.strip()
    lines = [
        f"# Review pack — {feat}: {fm.get('title') or fm.get('jira_summary', '')}",
        "",
        f"Draft hash: {hashing.short(digest)} · kind: {fm.get('kind', 'feature')}"
        + (f" · changes {fm['changes']}" if fm.get("changes") else ""),
        "",
        "## What it promises",
        summary.text if summary else "No card yet — read the story Goal.",
        "",
        "## Not yet reviewed by you",
    ]
    if last:
        diff = _git(base, "diff", "--unified=1", last, "--", str(p["story"]))
        changed = [
            ln for ln in diff.splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))
        ]
        lines.append(f"Changes since your last review (commit {last}): {len(changed)} lines.")
        lines += ["```diff", *changed[:80], "```"]
        if len(changed) > 80:
            lines.append(f"… {len(changed) - 80} more: git diff {last} -- {rel}")
    else:
        lines.append("First review: the whole story is new to you.")
    qs = _questions(base, feat)
    lines += ["", "## Assumptions and open questions", *(f"- {q}" for q in qs or ["None"])]
    if fm.get("changes") or fm.get("origin") == "as-is":
        lines += ["", "## Existing behaviour", "Read the analysis gap table before finalizing:"]
        lines += [f"- {a}" for a in _analyses(base, feat, fm)] or ["- None found"]
    result = check(base, feat) if p["debate"].is_file() else None
    lines += ["", "## Independent review"]
    if result is None:
        lines.append("Not run yet.")
    else:
        c = result["counts"]
        lines.append(
            f"Findings: {c['total']} · fixed {c['accepted']} · rebutted {c['rebutted']} · "
            f"open {c['open']} · independence: {result['independence']}"
        )
        for d in result["disputes"]:
            lines.append(f"- {d}")
    fsio.atomic_write(p["pack"], "\n".join(lines) + "\n")
    return p["pack"]


def brief(base: Path, feat: str) -> Path:
    p = _paths(base, feat)
    story = p["story"].read_text(encoding="utf-8")
    fm = frontmatter.parse(story).fm or {}
    srcs = sorted(set(re.findall(r"SRC-\d{4}", story)))
    files = [p["story"].relative_to(base).as_posix()]
    if p["card"].is_file():
        files.append(p["card"].relative_to(base).as_posix())
    for s in srcs:
        files += [x.relative_to(base).as_posix() for x in (base / "00-inbox").glob(f"{s}--*.md")]
    if fm.get("changes"):
        t = str(fm["changes"]).split(":")[-1]
        files.append(f"02-drafts/{t}.story.md")
    files += _analyses(base, feat, fm)
    lines = [
        f"# Reviewer brief — {feat}",
        "",
        "You did not write this story. You have no chat history. Judge only the files below.",
        "Report problems only, each with evidence (an AC/BR/NFR ID, a SRC or CODE cite, or a",
        "quoted line). No praise, no style nits, at most 8 findings, most severe first.",
        "",
        "## Read only",
        *(f"- {f}" for f in files),
        "",
        "## Roles (one reviewer per role)",
        *(f"- {r}: {t}" for r, t in ROLE_BRIEF.items()),
        "",
        "## Severity",
        "- blocker: building or testing would go wrong or stall.",
        "- major: likely rework or a wrong behaviour in an edge case.",
        "- minor: clarity; safe to ship as is.",
        "",
        "## Output: rows for the Findings table",
        "| # | Role | Severity | Finding | Evidence | Response | Resolution |",
        "Leave Response and Resolution empty; the author fills them.",
        "",
        "## Second round",
        "You will see the author's Response and Resolution. For each rebuttal answer",
        "`holds` (keep it open) or `withdrawn` (resolved). Do not add new findings in round 2.",
    ]
    fsio.atomic_write(p["brief"], "\n".join(lines) + "\n")
    return p["brief"]


def start(base: Path, feat: str, independence: str) -> Path:
    p = _paths(base, feat)
    digest = hashing.draft_hash(p["story"].read_text(encoding="utf-8"))
    if p["debate"].is_file():
        old = p["debate"].read_text(encoding="utf-8")
        ofm = frontmatter.parse(old).fm or {}
        if digest in (ofm.get("reviewed_hash"), ofm.get("final_hash")):
            raise ValueError(f"{p['debate'].relative_to(base)} already covers this draft; edit it")
        # The draft changed (a merge or a send-back): keep earlier rounds, open a new one.
        body = frontmatter.parse(old).body
        prior = ofm.get("final_hash") or ofm.get("reviewed_hash")
        earlier = body.replace(
            "## Findings",
            f"## Earlier findings ({hashing.short(str(prior))})",
            1,
        )
        earlier = earlier.replace("## Verdict", "## Earlier verdict", 1)
    else:
        earlier = ""
    text = (
        "---\n"
        f'kind: debate\nfeature: {feat}\nreviewed_hash: {digest}\nfinal_hash: ""\n'
        f"independence: {independence}\nrounds: 0\ndate: {datetime.date.today().isoformat()}\n"
        "---\n\n## Findings\n\n"
        "| # | Role | Severity | Finding | Evidence | Response | Resolution |\n"
        "| --- | --- | --- | --- | --- | --- | --- |\n\n"
        "## Verdict\n\nPending\n"
    )
    if earlier:
        text += "\n" + earlier.strip() + "\n"
    fsio.atomic_write(p["debate"], text)
    return p["debate"]


def _rows(body: str) -> list[dict[str, str]]:
    sec = markdown.sections(body).get("Findings")
    rows, header = [], None
    for _, line in sec.lines if sec else []:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(s.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        rows.append(dict(zip(header, cells, strict=False)))
    return rows


def check(base: Path, feat: str) -> dict:
    p = _paths(base, feat)
    if not p["debate"].is_file():
        return {"finalizable": False, "findings": ["no debate record; run the independent review"]}
    parsed = frontmatter.parse(p["debate"].read_text(encoding="utf-8"))
    fm = parsed.fm or {}
    now = hashing.draft_hash(p["story"].read_text(encoding="utf-8"))
    rows = _rows(parsed.body)
    problems, disputes = [], []
    counts = {"total": len(rows), "accepted": 0, "rebutted": 0, "open": 0, "blocker_open": 0}
    for r in rows:
        rid = r.get("#", "?")
        role, sev = r.get("role", "").lower(), r.get("severity", "").lower()
        resp, res = r.get("response", "").lower(), r.get("resolution", "")
        if role not in ROLES or sev not in SEVERITY:
            problems.append(f"{rid}: role must be {'/'.join(ROLES)}, severity {'/'.join(SEVERITY)}")
        if not EVIDENCE.search(r.get("evidence", "")):
            problems.append(
                f"{rid}: finding has no evidence (ID, cite or line); drop it or add one"
            )
        if resp not in RESPONSE:
            problems.append(f"{rid}: author response missing (accepted, rebutted or open)")
            continue
        counts[resp] += 1
        if resp == "accepted" and not res:
            problems.append(f"{rid}: accepted needs the fix in Resolution")
        if resp == "rebutted":
            if not EVIDENCE.search(res):
                problems.append(f"{rid}: a rebuttal needs evidence in Resolution")
            elif "holds" in res.lower() and sev != "minor":
                disputes.append(
                    f"{rid} ({sev}, {role}): {r.get('finding', '')[:100]} — reviewer holds"
                )
        if resp == "open":
            if not re.search(r"Q-\d{3}|owner", res, re.I):
                problems.append(f"{rid}: open needs a Q-NNN or 'owner' in Resolution")
            disputes.append(f"{rid} ({sev}, {role}): {r.get('finding', '')[:100]} — {res}")
            if sev == "blocker":
                counts["blocker_open"] += 1
    if not rows and str(fm.get("rounds", "0")) == "0":
        problems.append("no findings and no round recorded; run the reviewers")
    final = str(fm.get("final_hash") or "")
    if counts["accepted"] and final != now:
        problems.append("fixes were accepted: run `debate.py seal` after editing the draft")
    elif final and final != now:
        problems.append("the draft changed after sealing; review the change again")
    elif not counts["accepted"] and fm.get("reviewed_hash") != now and final != now:
        problems.append("the draft changed after review; review the change again")
    return {
        "feature": feat,
        "independence": fm.get("independence", "unknown"),
        "counts": counts,
        "disputes": disputes,
        "findings": problems,
        "finalizable": not problems and counts["blocker_open"] == 0,
    }


def seal(base: Path, feat: str) -> str:
    p = _paths(base, feat)
    text = p["debate"].read_text(encoding="utf-8")
    now = hashing.draft_hash(p["story"].read_text(encoding="utf-8"))
    text = re.sub(r"^final_hash:.*$", f"final_hash: {now}", text, count=1, flags=re.M)
    m = re.search(r"^rounds:\s*(\d+)", text, re.M)
    rounds = int(m.group(1)) + 1 if m else 1
    text = re.sub(r"^rounds:.*$", f"rounds: {rounds}", text, count=1, flags=re.M)
    fsio.atomic_write(p["debate"], text)
    return now


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["pack", "brief", "start", "seal", "check"])
    parser.add_argument("--feat", required=True)
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--independence", choices=["subagent", "same-session"], default="subagent")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, args.feat, cwd, args.command != "check")
        base = workspace.scope_dir(root, scope)
        feat = args.feat.split(":")[-1]
        if not _paths(base, feat)["story"].is_file():
            raise ValueError(f"no story for {feat}")
        if args.command == "check":
            result = check(base, feat)
            print(json.dumps(result, indent=2))
            return 0 if result["finalizable"] else 1
        out = {
            "pack": lambda: pack(base, feat),
            "brief": lambda: brief(base, feat),
            "start": lambda: start(base, feat, args.independence),
            "seal": lambda: seal(base, feat),
        }[args.command]()
        print(out.relative_to(base).as_posix() if isinstance(out, Path) else out)
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
