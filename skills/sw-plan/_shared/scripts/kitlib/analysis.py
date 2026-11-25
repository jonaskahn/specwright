"""Intended versus actual: code citations and the gap table of an analysis file.

An analysis compares, criterion by criterion, what a feature should do (documents, Jira, the
owner) with what the code and tests do today. Code and documents weigh the same; when they
disagree the row is ``divergent`` and a Q record holds both quotes.

Code is cited as ``CODE:<root>/<path>:L<a>[-L<b>]#<8 hex>``: the hash covers the cited lines,
so a later edit to them makes the citation stale.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from kitlib import frontmatter, markdown

STATUSES = ("done", "partial", "missing", "divergent", "unknown")
CONFIDENCE = ("high", "medium", "low")
CODE_CITE = re.compile(r"CODE:([\w.@-]+)/([^\s:;|]+):L(\d+)(?:-L(\d+))?#([0-9a-f]{8})")
DOC_CITE = re.compile(r"SRC-\d{4}:L\d+|\bAC-\d{3}-\d+\b")  # a source line, or a story AC
JIRA_KEY = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-\d+\b")
# A Q record once the feature exists; ASK-n inside the analysis before it does.
Q_REF = re.compile(r"\b(?:Q-\d{3}|ASK-\d+)\b")
TEST_PATH = re.compile(r"(test|spec|__tests__)", re.I)


def _lines_hash(lines: list[str]) -> str:
    text = "\n".join(line.rstrip() for line in lines)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


def cite(roots: dict[str, Path], ref: str, start: int, end: int | None = None) -> str:
    """CODE citation for lines start..end of <root>/<path>."""
    name, _, rel = ref.partition("/")
    if name not in roots:
        raise ValueError(f"unknown code root {name!r}; known: {', '.join(sorted(roots)) or 'none'}")
    path = (roots[name] / rel).resolve()
    if roots[name].resolve() not in path.parents or not path.is_file():
        raise ValueError(f"not a file inside {name}: {rel}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    end = end or start
    if not (1 <= start <= end <= len(lines)):
        raise ValueError(f"lines {start}-{end} outside 1-{len(lines)}")
    span = f"L{start}" + (f"-L{end}" if end != start else "")
    return f"CODE:{name}/{rel}:{span}#{_lines_hash(lines[start - 1 : end])}"


def verify_cite(roots: dict[str, Path], match: re.Match) -> str | None:
    """None when the citation still matches the code; else the reason it does not."""
    name, rel, a, b, digest = match.groups()
    if name not in roots:
        return f"unknown code root {name}"
    path = roots[name] / rel
    if not path.is_file():
        return f"file gone: {name}/{rel}"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start, end = int(a), int(b or a)
    if end > len(lines):
        return f"lines out of range: {name}/{rel}:L{start}-L{end}"
    if _lines_hash(lines[start - 1 : end]) != digest:
        return f"stale: {name}/{rel}:L{start}-L{end} changed since cited"
    return None


def _table(section) -> list[dict[str, str]]:
    rows, header = [], None
    for number, line in section.lines if section else []:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set(s.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        row = dict(zip(header, cells))
        row["_line"] = str(number)
        rows.append(row)
    return rows


def check(path: Path, roots: dict[str, Path]) -> dict[str, Any]:
    """Validate an analysis file and summarise its gap shape."""
    text = path.read_text(encoding="utf-8")
    parsed = frontmatter.parse(text)
    findings: list[str] = []
    if parsed.error or not parsed.fm:
        return {"findings": [f"{path.name}: front matter unreadable"], "rows": []}
    secs = markdown.sections(parsed.body)
    rows = _table(secs.get("Criteria"))
    conflicts = secs.get("Conflicts").text if secs.get("Conflicts") else ""
    if not rows:
        findings.append("Criteria table is empty")
    counts = {s: 0 for s in STATUSES}
    ask, accepted = [], []
    for row in rows:
        rid = row.get("#") or row.get("id") or f"line {row['_line']}"
        status = row.get("status", "").lower()
        conf = row.get("confidence", "").lower()
        actual = row.get("actual", "")
        intended = row.get("intended", "")
        if status not in STATUSES:
            findings.append(f"{rid}: status must be one of {', '.join(STATUSES)}")
            continue
        counts[status] += 1
        if conf not in CONFIDENCE:
            findings.append(f"{rid}: confidence must be high, medium or low")
        cites = list(CODE_CITE.finditer(actual))
        if status in ("done", "partial", "divergent") and not cites:
            findings.append(f"{rid}: {status} needs at least one CODE citation in Actual")
        if status == "divergent" and not Q_REF.search(conflicts + " " + row.get("notes", "")):
            findings.append(f"{rid}: divergent needs a Q-NNN or ASK-n named in Conflicts")
        if status in ("done", "partial", "divergent") and not cites and not roots:
            findings.append(
                f"{rid}: no code root registered, so the actual side can only be missing or unknown"
            )
        if not (
            DOC_CITE.search(intended)
            or JIRA_KEY.search(intended)
            or intended.lower() in ("owner", "observed")
            or Q_REF.search(intended)
        ):
            findings.append(
                f"{rid}: Intended needs SRC-NNNN:Lnn, a Jira key, owner, observed or a Q id"
            )
        for m in cites:
            problem = verify_cite(roots, m)
            if problem:
                findings.append(f"{rid}: {problem}")
        has_test = any(TEST_PATH.search(m.group(2)) for m in cites)
        if status == "done" and conf == "high" and (has_test or len(cites) >= 2):
            accepted.append(rid)
        else:
            ask.append(
                {
                    "row": rid,
                    "status": status,
                    "confidence": conf,
                    "criterion": row.get("criterion", "")[:120],
                }
            )
    total = sum(counts.values())
    # A verification analysis (`verifies: FEAT-NNN`) has one row per AC of that story.
    verifies = str(parsed.fm.get("verifies") or "").split(":")[-1]
    verified = None
    if verifies:
        story = path.parents[2] / "02-drafts" / f"{verifies}.story.md"
        if story.is_file():
            sp = frontmatter.parse(story.read_text(encoding="utf-8"))
            want = set(markdown.ac_blocks(markdown.sections(sp.body).get("Acceptance criteria")))
            have = {(r.get("#") or "").strip() for r in rows}
            for missing in sorted(want - have):
                findings.append(f"{missing}: no verification row for this criterion of {verifies}")
            verified = not (want - have) and counts["done"] == total and total > 0
        else:
            findings.append(f"verifies {verifies}, which has no story")
    if total == 0:
        shape = "empty"
    elif counts["missing"] == total:
        shape = "new"
    elif counts["done"] == total:
        shape = "as-is"
    elif counts["divergent"] and counts["divergent"] + counts["done"] == total:
        shape = "fix"
    elif counts["missing"] + counts["partial"] and counts["divergent"] == 0:
        shape = "complete"
    else:
        shape = "mixed"
    recommend = {
        "new": "sw-spec: a new story (nothing is built yet)",
        "as-is": "sw-spec: confirmed behaviour becomes version 1; a change follows if wanted",
        "complete": "sw-spec: version 1 from done rows, then a completion change for the gaps",
        "fix": "answer the divergences: code wrong → a fix; spec wrong → a correction",
        "mixed": "answer the questions first; then version 1 plus a completion change",
        "empty": "fill the Criteria table",
    }[shape]
    if verifies:
        recommend = (
            f"sw-spec: ship and merge {verifies} (merge.py ship, then finish)"
            if verified
            else f"{verifies} is not fully in the code: implement the gaps, or ship with "
            "--accept-gaps and the owner's reason"
        )
    return {
        "target": parsed.fm.get("target"),
        "status": parsed.fm.get("status"),
        "counts": counts,
        "shape": shape,
        "recommend": recommend,
        "verifies": verifies or None,
        "verified": verified,
        "auto_accepted": accepted,
        "ask": ask,
        "findings": findings,
        "pass": not findings,
    }
