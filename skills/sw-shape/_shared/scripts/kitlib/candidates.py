"""Candidate extraction by several workers, with one writer per file and checks by program.

A worker reads only the snapshots assigned to it and writes one file, `CAND-NNN--<area>.md`, in
`01-analysis/candidates/`. The file lists claims in one table with a citation each; workers never
write records, registries or each other's files. `assignment.tsv` records who reads what, so a
script can confirm that every snapshot was read exactly once, every citation resolves and the
counts add up. Worker claims stay unverified until that check passes or a named person reviews them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kitlib import cite, frontmatter, fsio, ids, tables

FOLDER = "01-analysis/candidates"
ASSIGNMENT = "assignment.tsv"
HEADER = ["#", "Kind", "Topic", "Claim", "Citation", "Status", "Note"]
STATUSES = ("raw", "accepted", "rejected", "merged")
KINDS = ("rule", "number", "actor", "term", "constraint", "other")
TARGET_WORDS = 18000
MAX_CLAIM_WORDS = 40
MAX_BODY_WORDS = 2500
ITEM_KEY = re.compile(r"^(?:[A-Z]{2,5}:)?(CAND-\d{3})\.(\d+)$")


@dataclass
class Item:
    worker: str
    number: int
    kind: str
    topic: str
    claim: str
    citations: list[str]
    status: str
    note: str

    @property
    def key(self) -> str:
        return f"{self.worker}.{self.number}"


def folder(base: Path) -> Path:
    return base / FOLDER


def read_assignment(base: Path) -> list[dict[str, str]]:
    path = folder(base) / ASSIGNMENT
    if not path.is_file():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.startswith("#"):
            parts = raw.split("\t")
            if len(parts) == 4:
                rows.append(dict(zip(("worker", "area", "snapshot", "words"), parts, strict=True)))
    return rows


def _worker_files(base: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(folder(base).glob("CAND-*.md")):
        identity = ids.id_from_name(path.name)
        if identity:
            found[identity] = path
    return found


def parse_worker(path: Path) -> tuple[dict, list[Item], list[str]]:
    """Front matter, items and format problems of one worker file."""
    parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
    fm = parsed.fm or {}
    problems: list[str] = []
    worker = str(fm.get("id", ""))
    doc = tables.parse(parsed.body)
    items: list[Item] = []
    if doc.table is None:
        problems.append("no candidates table")
        return fm, items, problems
    if doc.table.header != HEADER:
        problems.append(f"table columns must be {' | '.join(HEADER)}")
        return fm, items, problems
    for row in doc.table.rows:
        number = row[0].strip()
        if not number.isdigit():
            problems.append(f"row '{number}': # must be a number")
            continue
        citations = [c.text() for c in cite.find(row[4])]
        items.append(
            Item(
                worker,
                int(number),
                row[1].strip().lower(),
                row[2].strip(),
                row[3].strip(),
                citations,
                row[5].strip().lower(),
                "" if row[6] == tables.EMPTY else row[6].strip(),
            )
        )
    return fm, items, problems


def all_items(base: Path) -> list[Item]:
    found: list[Item] = []
    for path in _worker_files(base).values():
        found.extend(parse_worker(path)[1])
    return found


def item(base: Path, key: str) -> Item:
    match = ITEM_KEY.match(key.strip())
    if not match:
        raise ValueError(f"'{key}' is not a candidate key like CAND-003.7")
    worker, number = match.group(1), int(match.group(2))
    for found in all_items(base):
        if found.worker == worker and found.number == number:
            return found
    raise ValueError(f"no candidate {worker}.{number}")


def item_citations(base: Path, key: str) -> list[str]:
    """The citations of one candidate, so a question can cite it by key."""
    found = item(base, key)
    if not found.citations:
        raise ValueError(f"{key} has no citation to raise a question from")
    return found.citations


def _words(path: Path) -> int:
    return len(frontmatter.parse(path.read_text(encoding="utf-8")).body.split())


def _root_title(base: Path, fm: dict, by_id: dict[str, dict]) -> str:
    seen: set[str] = set()
    current = fm
    while current.get("source_parent") and str(current["source_parent"]) not in seen:
        seen.add(str(current["source_parent"]))
        parent = by_id.get(str(current["source_parent"]))
        if parent is None:
            break
        current = parent
    return str(current.get("title") or current.get("id"))


def plan_assignment(
    base: Path, scope: str, target_words: int = TARGET_WORDS, today: str = ""
) -> tuple[list[dict[str, str]], dict[Path, str]]:
    """Assign every unassigned snapshot to a worker; returns new rows and the worker files."""
    done = {r["snapshot"] for r in read_assignment(base)}
    headers: dict[str, dict] = {}
    words: dict[str, int] = {}
    for path in sorted((base / "00-inbox").glob("SRC-*.md")):
        fm = frontmatter.parse(path.read_text(encoding="utf-8")).fm or {}
        if fm.get("id") and fm.get("status") != "withdrawn":
            headers[str(fm["id"])] = fm
            words[str(fm["id"])] = _words(path)
    areas: dict[str, list[str]] = {}
    for src in sorted(headers):
        if src in done:
            continue
        fm = headers[src]
        area = ids.slugify(_root_title(base, fm, headers)) or "general"
        if not fm.get("source_parent") and fm.get("labels"):
            area = ids.slugify(str(fm["labels"][0])) or area
        areas.setdefault(area, []).append(src)
    taken = ids.taken_ids(base)
    rows: list[dict[str, str]] = []
    files: dict[Path, str] = {}
    for area in sorted(areas):
        groups: list[list[str]] = [[]]
        total = 0
        for src in areas[area]:
            if groups[-1] and total + words[src] > target_words:
                groups.append([])
                total = 0
            groups[-1].append(src)
            total += words[src]
        for number, group in enumerate(groups, 1):
            label = area if len(groups) == 1 else f"{area}-{number}"
            worker = ids.next_id("CAND", taken)
            taken.append(worker)
            rows += [
                {"worker": worker, "area": label, "snapshot": s, "words": str(words[s])}
                for s in group
            ]
            fm = {
                "id": worker,
                "type": "candidates",
                "scope": scope,
                "title": f"Candidates: {label}",
                "aliases": [],
                "status": "raw",
                "covers": group,
                "count": 0,
                "sources": group,
                "supersedes": [],
                "created": today,
            }
            body = (
                "## Covered\n\n"
                + "\n".join(f"- {s}" for s in group)
                + "\n\n## Candidates\n\n"
                + tables.Table(list(HEADER)).render()
            )
            files[folder(base) / ids.record_filename(worker, fm["title"])] = frontmatter.render(
                fm, body
            )
    return rows, files


def assignment_text(rows: list[dict[str, str]], existing: bool) -> str:
    head = "" if existing else "# worker\tarea\tsnapshot\twords\n"
    return head + "".join(
        f"{r['worker']}\t{r['area']}\t{r['snapshot']}\t{r['words']}\n" for r in rows
    )


def check(base: Path) -> list[str]:
    """Coverage, citation, format and count problems; empty when the extraction is sound."""
    problems: list[str] = []
    rows = read_assignment(base)
    snapshots = sorted(
        ids.id_from_name(p.name)
        for p in (base / "00-inbox").glob("SRC-*.md")
        if (frontmatter.parse(p.read_text(encoding="utf-8")).fm or {}).get("status") != "withdrawn"
    )
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["snapshot"]] = counts.get(r["snapshot"], 0) + 1
    for src in snapshots:
        if counts.get(src, 0) == 0:
            problems.append(f"{src}: not assigned to any worker")
    problems += [f"{s}: assigned {n} times" for s, n in sorted(counts.items()) if n > 1]
    problems += [
        f"{s}: assigned but not in the inbox" for s in sorted(counts) if s not in snapshots
    ]
    workers = _worker_files(base)
    sources = cite.Sources(base)
    keys: set[str] = set()
    for worker in sorted({r["worker"] for r in rows}):
        if worker not in workers:
            problems.append(f"{worker}: assigned but its file is missing")
            continue
        path = workers[worker]
        fm, found, format_problems = parse_worker(path)
        problems += [f"{worker}: {p}" for p in format_problems]
        assigned = sorted(r["snapshot"] for r in rows if r["worker"] == worker)
        if sorted(str(x) for x in fm.get("covers") or []) != assigned:
            problems.append(f"{worker}: covers does not match the assignment")
        if fm.get("count") != len(found):
            problems.append(f"{worker}: count is {fm.get('count')} but the table has {len(found)}")
        body = frontmatter.parse(path.read_text(encoding="utf-8")).body
        if len(body.split()) > MAX_BODY_WORDS:
            problems.append(f"{worker}: over the {MAX_BODY_WORDS} word cap")
        numbers = [i.number for i in found]
        if numbers != list(range(1, len(found) + 1)):
            problems.append(f"{worker}: item numbers must run 1..{len(found)} without gaps")
        for it in found:
            keys.add(it.key)
        for it in found:
            problems += _item_problems(it, assigned, keys, sources)
    for worker in sorted(set(workers) - {r["worker"] for r in rows}):
        problems.append(f"{worker}: has a file but no assignment")
    return sorted(set(problems))


def _item_problems(
    it: Item, assigned: list[str], keys: set[str], sources: cite.Sources
) -> list[str]:
    out = []
    if it.kind not in KINDS:
        out.append(f"{it.key}: kind must be one of {', '.join(KINDS)}")
    if it.status not in STATUSES:
        out.append(f"{it.key}: status must be one of {', '.join(STATUSES)}")
    if not it.topic or not it.claim:
        out.append(f"{it.key}: topic and claim are required")
    if len(it.claim.split()) > MAX_CLAIM_WORDS:
        out.append(f"{it.key}: claim is over {MAX_CLAIM_WORDS} words; summarize, do not copy")
    if not it.citations:
        out.append(f"{it.key}: needs a citation like SRC-0001:L12#a1b2")
    for c in cite.find(" ".join(it.citations)):
        if c.source not in assigned:
            out.append(f"{it.key}: cites {c.source}, which is not assigned to {it.worker}")
        for problem in cite.problems(sources, c.text(), require_hash=True):
            if problem.severity == "error":
                out.append(f"{it.key}: {problem.message}")
    if it.status == "merged" and not ITEM_KEY.match(it.note):
        out.append(f"{it.key}: a merged candidate names the one it merged into in Note")
    return out


def _topic(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def conflicts(base: Path) -> list[tuple[Item, Item]]:
    """Pairs on the same topic that make different claims, both still in play."""
    live = [i for i in all_items(base) if i.status in ("raw", "accepted")]
    found = []
    for n, a in enumerate(live):
        for b in live[n + 1 :]:
            same = _topic(a.topic) == _topic(b.topic)
            if same and cite.normalize(a.claim).casefold() != cite.normalize(b.claim).casefold():
                found.append((a, b))
    return found


def set_status(base: Path, key: str, status: str, into: str = "") -> tuple[Path, str]:
    """The worker file with one item's status changed; nothing is written here."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    target = item(base, key)
    if status == "merged":
        into_item = item(base, into)
        if into_item.key == target.key:
            raise ValueError("an item cannot merge into itself")
    path = _worker_files(base)[target.worker]
    doc = tables.parse(path.read_text(encoding="utf-8"))
    if doc.table is None:
        raise ValueError("no candidates table")
    for row in doc.table.rows:
        if row[0].strip() == str(target.number):
            row[5] = status
            row[6] = into if status == "merged" else (tables.EMPTY if status == "raw" else row[6])
    return path, doc.render()


def write_text(path: Path, text: str) -> None:
    fsio.atomic_write(path, text)
