#!/usr/bin/env python3
"""Change and fix stories: bind to the feature they change, check the delta, ship, merge.

A change or fix is a feature story (FEAT-NNN) with `kind: change|fix`, `changes: FEAT-TTT` and
`base_hash` (the target's draft hash when the change was written). Its `### Delta` table (inside
Context, so the twelve sections stay canonical) maps
target criteria to actions; `### Must not change` lists target criteria that stay as they are.

    merge.py v1     --feat FEAT-NNN --analysis <target>
                                                 record version 1 of an existing feature from a
                                                 confirmed analysis (origin: as-is)
    merge.py base   --change FEAT-NNN            record the target's current hash as base_hash
    merge.py check  --change FEAT-NNN            base still current, delta rows valid
    merge.py ship   --change FEAT-NNN [--commit ROOT@REF ...] [--accept-gaps REASON]
                                                 mark shipped; needs a passing pre-ship analysis
                                                 (analyze.py new FEAT-NNN --verify); records the
                                                 git commit of every code root
    merge.py finish --change FEAT-NNN            after the agent edited the target: verify the
                                                 target reflects every delta row, bump its version,
                                                 add a changelog line, mark the change superseded

Common: --cwd <project> [--scope S]. Merging changes the target's text, so the target goes back
to sw-review for the owner's finalize; this script records no approval.
Exit codes: 0 ok, 1 check findings, 2 usage or file error.
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

from kitlib import analysis, coderoots, frontmatter, fsio, hashing, markdown, workspace  # noqa: E402

ACTIONS = ("add", "change", "remove", "keep")
ACCEPTED = ("ready-to-publish", "published", "ready-for-dev", "in-development")
AC_ID = re.compile(r"AC-\d{3}-\d+")


def _story(base: Path, feat: str) -> Path:
    return base / "02-drafts" / f"{feat}.story.md"


def _load(path: Path):
    text = path.read_text(encoding="utf-8")
    parsed = frontmatter.parse(text)
    if parsed.error or not parsed.fm:
        raise ValueError(f"{path.name}: front matter unreadable")
    return text, parsed


def _set_fm(text: str, key: str, value: str) -> str:
    """Set one scalar front-matter key in place (added before the closing ---)."""
    head, sep, body = text.partition("\n---\n")
    if re.search(rf"^{key}:.*$", head, re.M):
        head = re.sub(rf"^{key}:.*$", f"{key}: {value}", head, count=1, flags=re.M)
    else:
        head = head + f"\n{key}: {value}"
    return head + sep + body


def _norm(text: str) -> str:
    return re.sub(r"[\s*_`]+", " ", text).strip().lower()


def _acs(parsed) -> dict:
    return markdown.ac_blocks(markdown.sections(parsed.body).get("Acceptance criteria"))


def _sub(parsed, name: str):
    """A '### name' subsection of Context (the twelve top-level sections stay canonical)."""
    return markdown.sections(parsed.body, level=3).get(name)


def _delta(parsed) -> list[dict]:
    sec = _sub(parsed, "Delta")
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
        rows.append(dict(zip(header, cells)))
    return rows


def check(base: Path, change: str) -> dict:
    ctext, cp = _load(_story(base, change))
    fm = cp.fm
    findings = []
    kind = fm.get("kind")
    if kind not in ("change", "fix"):
        return {"findings": [f"{change}: kind must be change or fix"], "rows": []}
    target = str(fm.get("changes", "")).split(":")[-1]
    tpath = _story(base, target)
    if not tpath.is_file():
        return {"findings": [f"{change}: target {target or '?'} has no story"], "rows": []}
    ttext, tp = _load(tpath)
    now = hashing.draft_hash(ttext)
    if fm.get("base_hash") != now:
        findings.append(
            f"{target} changed since {change} was written; rebase the change (merge.py base)"
        )
    tacs, cacs = _acs(tp), _acs(cp)
    rows = _delta(cp)
    if not rows:
        findings.append("Delta table is empty")
    for r in rows:
        tid, action, src = r.get("target", ""), r.get("action", "").lower(), r.get("source", "")
        if action not in ACTIONS:
            findings.append(f"{tid}: action must be one of {', '.join(ACTIONS)}")
            continue
        if action in ("change", "remove", "keep") and tid not in tacs:
            findings.append(f"{tid}: not an active criterion of {target}")
        if action in ("add", "change"):
            sid = (AC_ID.findall(src) or [""])[0]
            if sid not in cacs:
                findings.append(f"{tid or 'new'}: source {src or '?'} is not an AC of {change}")
        if action == "add" and tid not in ("new", "", "-"):
            findings.append(f"{tid}: an added criterion has target 'new'")
        if action == "remove" and not src:
            findings.append(f"{tid}: remove needs a reason in Source")
    keep = _sub(cp, "Must not change")
    keep_ids = AC_ID.findall(keep.text) if keep else []
    if not keep_ids and kind == "change":
        findings.append("Must not change lists no target criterion (regression guard)")
    for k in keep_ids:
        if k not in tacs:
            findings.append(f"Must not change: {k} is not an active criterion of {target}")
    return {
        "change": change,
        "target": target,
        "kind": kind,
        "rows": rows,
        "keep": keep_ids,
        "findings": findings,
        "pass": not findings,
    }


def _commits(root: Path, scope: str, given: list[str]) -> list[str]:
    if given:
        return given
    out = []
    for r in coderoots.registered(root, scope):
        if not r["exists"]:
            continue
        done = subprocess.run(
            ["git", "-C", r["abs"], "rev-parse", "--short=12", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if done.returncode == 0:
            out.append(f"{r['name']}@{done.stdout.strip()}")
    return out


def _verification(root: Path, scope: str, base: Path, change: str) -> dict:
    path = base / "01-analysis" / "as-is" / f"{change}.verify.analysis.md"
    if not path.is_file():
        return {
            "verified": False,
            "why": f"no pre-ship analysis; run analyze.py new {change} --verify",
        }
    roots = {r["name"]: Path(r["abs"]) for r in coderoots.registered(root, scope) if r["exists"]}
    result = analysis.check(path, roots)
    if result["findings"]:
        return {"verified": False, "why": "; ".join(result["findings"][:3])}
    if not result["verified"]:
        gaps = {k: v for k, v in result["counts"].items() if k != "done" and v}
        return {"verified": False, "why": f"criteria not done in code: {gaps}"}
    return {"verified": True, "why": ""}


def ship(
    root: Path, scope: str, base: Path, change: str, given: list[str], accept_gaps: str | None
) -> dict:
    path = _story(base, change)
    text, cp = _load(path)
    if cp.fm.get("status") not in ACCEPTED:
        raise ValueError(f"{change} is {cp.fm.get('status')}; only a finalized change ships")
    result = check(base, change)
    if result["findings"]:
        raise ValueError("delta check fails: " + "; ".join(result["findings"][:3]))
    verified = _verification(root, scope, base, change)
    if not verified["verified"]:
        if not accept_gaps:
            raise ValueError("pre-ship check: " + verified["why"] + " (or --accept-gaps REASON)")
        text = _set_fm(text, "ship_note", json.dumps(f"shipped with gaps: {accept_gaps}"))
    commits = _commits(root, scope, given)
    if not commits:
        raise ValueError("no git commit to record; pass --commit <root>@<ref>")
    text = _set_fm(text, "shipped", f"[{', '.join(commits)}]")
    text = _set_fm(text, "shipped_date", datetime.date.today().isoformat())
    fsio.atomic_write(path, text)
    return {
        "shipped": commits,
        "verified": verified["verified"],
        "merge": result["rows"],
        "next": "edit the target per merge rows, then merge.py finish",
    }


def finish(base: Path, change: str) -> dict:
    cpath = _story(base, change)
    ctext, cp = _load(cpath)
    if not cp.fm.get("shipped"):
        raise ValueError(f"{change} is not shipped; run merge.py ship first")
    target = str(cp.fm.get("changes")).split(":")[-1]
    tpath = _story(base, target)
    ttext, tp = _load(tpath)
    tacs, cacs = _acs(tp), _acs(cp)
    tombs = markdown.ac_tombstones(markdown.sections(tp.body).get("Acceptance criteria"))
    texts = {_norm(b.text) for b in tacs.values()}
    findings = []
    for r in _delta(cp):
        action, tid = r.get("action", "").lower(), r.get("target", "")
        sid = (AC_ID.findall(r.get("source", "")) or [""])[0]
        if action in ("add", "change") and sid in cacs and _norm(cacs[sid].text) not in texts:
            findings.append(f"{sid}: its text is not in {target} yet ({action})")
        if action == "change" and tid in tacs and _norm(tacs[tid].text) != _norm(cacs[sid].text):
            findings.append(f"{tid}: still has the old text")
        if action == "remove" and (tid in tacs or tid not in tombs):
            findings.append(f"{tid}: must be a tombstone line '~~{tid}~~ withdrawn — {change}'")
    # Rules travel with the change: every rule line of the change must now be in the target.
    crules = markdown.sections(cp.body).get("Business rules")
    trules = markdown.sections(tp.body).get("Business rules")
    have = {_norm(x) for _, x in (trules.lines if trules else []) if x.strip()}
    for _, line in crules.lines if crules else []:
        if line.strip().startswith("- ") and _norm(line) not in have:
            findings.append(f"business rule not in {target}: {line.strip()[:80]}")
    if findings:
        return {"findings": findings, "pass": False}
    version = int(tp.fm.get("version") or 1) + 1
    shipped = cp.fm.get("shipped")
    shipped = ", ".join(shipped) if isinstance(shipped, list) else str(shipped)
    line = f"v{version} {change} {shipped} {datetime.date.today().isoformat()}"
    log = tp.fm.get("changelog") or []
    log = log if isinstance(log, list) else [str(log)]
    ttext = _set_fm(ttext, "version", str(version))
    ttext = _set_fm(ttext, "changelog", json.dumps([*log, line], ensure_ascii=False))
    fsio.atomic_write(tpath, ttext)
    ctext = _set_fm(ctext, "status", "superseded")
    ctext = _set_fm(ctext, "merged_into", f"{target}@v{version}")
    fsio.atomic_write(cpath, ctext)
    return {
        "pass": True,
        "target": target,
        "version": version,
        "changelog": line,
        "next": f"{target} text changed: it returns to sw-review for your finalize",
    }


def v1(root: Path, scope: str, base: Path, feat: str, target: str) -> dict:
    """Mark a story as version 1 of an existing feature, from a confirmed analysis."""
    path = base / "01-analysis" / "as-is" / f"{target}.analysis.md"
    if not path.is_file():
        raise ValueError(f"no analysis {target}")
    afm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
    if afm.get("status") != "confirmed":
        raise ValueError(f"analysis {target} is not confirmed; analyze.py confirm {target} first")
    spath = _story(base, feat)
    text, sp = _load(spath)
    if int(sp.fm.get("version") or 1) > 1:
        raise ValueError(
            f"{feat} is already version {sp.fm.get('version')}; v1 records only a first version"
        )
    rel = path.relative_to(base).as_posix()
    for key, value in (("origin", "as-is"), ("version", "1"), ("analysis", rel)):
        text = _set_fm(text, key, value)
    fsio.atomic_write(spath, text)
    return {"feature": feat, "origin": "as-is", "version": 1, "analysis": rel}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["v1", "base", "check", "ship", "finish"])
    parser.add_argument("--change")
    parser.add_argument("--feat", help="v1: the story to mark")
    parser.add_argument("--analysis", help="v1: the confirmed analysis target")
    parser.add_argument("--accept-gaps", metavar="REASON", help="ship despite verification gaps")
    parser.add_argument("--commit", action="append", default=[])
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        item = args.change or args.feat
        if not item:
            raise ValueError("--change (or --feat for v1) is required")
        scope = workspace.resolve(root, args.scope, item, cwd, args.command != "check")
        base = workspace.scope_dir(root, scope)
        change = item.split(":")[-1]
        if args.command == "v1":
            if not (args.feat and args.analysis):
                raise ValueError("usage: v1 --feat FEAT-NNN --analysis <target>")
            print(json.dumps(v1(root, scope, base, change, args.analysis)))
            return 0
        if args.command == "base":
            text, cp = _load(_story(base, change))
            target = str(cp.fm.get("changes", "")).split(":")[-1]
            ttext, _ = _load(_story(base, target))
            digest = hashing.draft_hash(ttext)
            fsio.atomic_write(_story(base, change), _set_fm(text, "base_hash", digest))
            print(json.dumps({"change": change, "target": target, "base_hash": digest}))
            return 0
        if args.command == "check":
            result = check(base, change)
            print(json.dumps(result, indent=2))
            return 0 if not result["findings"] else 1
        if args.command == "ship":
            print(
                json.dumps(ship(root, scope, base, change, args.commit, args.accept_gaps), indent=2)
            )
            return 0
        result = finish(base, change)
        print(json.dumps(result, indent=2))
        return 0 if result["pass"] else 1
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
