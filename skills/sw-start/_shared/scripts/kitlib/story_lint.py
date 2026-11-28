"""Review checks that the story compiler and the lint gate share."""

from __future__ import annotations

import json
import re
from pathlib import Path

from kitlib import cite, ids, paths, schema, task_validation, workspace
from kitlib import compile as compiler

_FILLER = (
    re.compile(r"<[^>\n]+>"),
    re.compile(r"is exercised", re.I),
    re.compile(r"the context of", re.I),
    re.compile(r"per-AC result", re.I),
    re.compile(r"observable:", re.I),
)
_NONE = re.compile(r"(?i)\A\s*none\s*\Z")
_REASONED = re.compile(r"(?i)\Anone\s*[—–-]\s*\S")
_NONE_SECTIONS = (
    "Edge cases and error behavior",
    "Non-functional",
    "UI/UX",
    "Out of scope",
    "Dependencies and relations",
    "Open questions",
)
_PLAN_STATUSES = {"ready-for-dev", "in-development", "done"}
_PLACEHOLDER = "None — not yet compiled."


def is_reasoned_none(text: str) -> bool:
    return bool(_REASONED.match(text.strip()))


def checks(doc, ctx, emit) -> None:
    """Emit L-071 and the later story, epic and plan findings for one document."""
    if doc.story and not doc.card:
        _story(doc, ctx, emit)
    if str(doc.path).startswith("tasks/"):
        _filler(doc.raw, doc, emit)
    if doc.fm.get("type") == "epic":
        _epic(doc, ctx, emit)
    _links(doc, ctx, emit)


def _story(doc, ctx, emit) -> None:
    _filler(doc.body, doc, emit)
    _then(doc, emit)
    _frontmatter(doc, emit)
    _nones(doc, ctx, emit)
    _coverage(doc, ctx, emit)
    _size(doc, ctx, emit)
    _plan(doc, ctx, emit)


def _filler(text: str, doc, emit) -> None:
    for pattern in _FILLER:
        match = pattern.search(text)
        if match:
            emit(
                "L-074",
                f"template filler {match.group(0)!r}",
                _line_of(text, match.start()),
                doc.spec_id,
            )


def _then(doc, emit) -> None:
    for acid, ac in doc.ac.items():
        given, then = _clause(ac.text, "Given"), _clause(ac.text, "Then")
        if given and then and (given in then or re.search(r"\bGiven\b", then)):
            emit("L-075", f"{acid}: Then repeats Given", ac.line, acid)


def _frontmatter(doc, emit) -> None:
    fm = doc.fm
    for key in schema.DROPPED_STORY_KEYS:
        if key in fm:
            emit(
                "L-077",
                f"drop stored {key}; publish derives it or aliases already hold it",
                1,
                doc.spec_id,
            )
    if isinstance(fm.get("epic"), list):
        emit("L-077", "epic is one id, not a list", 1, doc.spec_id)
    pairs = (
        ("br", "Business rules", "BR-"),
        ("nfr", "Non-functional", "NFR-"),
        ("assets", "UI/UX", "ASSET-"),
    )
    for key, section, prefix in pairs:
        body_ids = _prefixed(doc.text(section) + "\n" + doc.text("Context"), prefix)
        fm_ids = _listed(fm.get(key), prefix)
        if body_ids != fm_ids:
            emit(
                "L-077",
                f"{key}: {sorted(fm_ids) or '[]'} disagrees with {sorted(body_ids) or '[]'}",
                doc.line(section),
                doc.spec_id,
            )
    cited = {item.source for item in cite.find(doc.raw)}
    listed = {str(item).split(":")[-1] for item in (fm.get("sources") or [])}
    if cited != listed:
        emit(
            "L-077",
            f"sources: {sorted(listed) or '[]'} does not match citations {sorted(cited) or '[]'}",
            1,
            doc.spec_id,
        )


def _nones(doc, ctx, emit) -> None:
    legacy = [str(item) for item in doc.fm.get("legacy_ids") or []]
    coverage = _load_coverage(ctx.base, doc.spec_id) if legacy else None
    for name in _NONE_SECTIONS:
        if name not in doc.sec:
            continue
        text = doc.text(name).strip()
        if not text:
            continue
        if _NONE.match(text):
            emit("L-078", f"{name} is bare None; say None — and why", doc.line(name), doc.spec_id)
        elif text.lower().startswith("none") and legacy and not cite.find(text):
            emit("L-078", f"{name} cites no source line", doc.line(name), doc.spec_id)
    if coverage is None:
        return
    kinds = {row.get("disposition") for row in coverage.get("items") or []}
    ui = doc.text("UI/UX").strip()
    if "ui" in kinds and ui.lower().startswith("none"):
        emit("L-078", "UI/UX says None while the coverage map has a mockup", doc.line("UI/UX"))
    questions = doc.text("Open questions").strip()
    if any(
        row.get("disposition") == "q" for row in coverage.get("items") or []
    ) and questions.lower().startswith("none"):
        emit(
            "L-078",
            "Open questions says None while the coverage map has a gap",
            doc.line("Open questions"),
        )


def _coverage(doc, ctx, emit) -> None:
    legacy = [str(item) for item in doc.fm.get("legacy_ids") or []]
    if not legacy:
        return
    path = _coverage_path(ctx.base, doc.spec_id)
    if not path.is_file():
        emit("L-071", f"no coverage file at {path.name}", 1, doc.spec_id)
        return
    try:
        coverage = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        emit("L-071", f"coverage file is not readable: {exc}", 1, doc.spec_id)
        return
    source = str(coverage.get("source") or "")
    snapshot = ids.find_record(ctx.base / "sources", source) if source else None
    if snapshot is None:
        emit(
            "L-071",
            f"coverage names {source or 'no snapshot'}, which is not in sources/",
            1,
            source,
        )
        return
    for problem in compiler.coverage_problems(
        snapshot.read_text(encoding="utf-8"), source, coverage
    ):
        emit("L-071", problem, 1, doc.spec_id)
    known = {d.spec_id for d in ctx.docs if d.spec_id} | set(doc.ac)
    for row in coverage.get("items") or []:
        for key in ("target", "question"):
            ref = str(row.get(key) or "")
            ident = ref.split(":")[-1]
            if ident and ident not in known and not ident.startswith("AC-"):
                emit(
                    "L-071", f"coverage target {ident} does not exist", row.get("start") or 1, ident
                )


def _size(doc, ctx, emit) -> None:
    if len(doc.ac) > 7:
        emit(
            "L-080",
            f"{len(doc.ac)} acceptance criteria; the sizer target is 7",
            doc.line("Acceptance criteria"),
            doc.spec_id,
            "warn",
        )
    mine = _load_coverage(ctx.base, doc.spec_id)
    legacy = [str(item) for item in doc.fm.get("legacy_ids") or []]
    if not mine or len(legacy) != 1 or mine.get("sizing_dec"):
        return
    actor, page, source = mine.get("actor") or "", mine.get("page") or "", mine.get("source") or ""
    if not actor or not page:
        return
    for other in ctx.docs:
        if other.spec_id == doc.spec_id or not other.story or other.card:
            continue
        other_ids = [str(item) for item in other.fm.get("legacy_ids") or []]
        if len(other_ids) != 1:
            continue
        theirs = _load_coverage(ctx.base, other.spec_id)
        if not theirs or theirs.get("sizing_dec"):
            continue
        if (
            theirs.get("source") == source
            and (theirs.get("actor") or "").casefold() == actor.casefold()
            and (theirs.get("page") or "").casefold() == page.casefold()
        ):
            emit(
                "L-080",
                f"{legacy[0]} and {other_ids[0]} share an actor and screen and were not bundled",
                1,
                doc.spec_id,
            )
            return


def _plan(doc, ctx, emit) -> None:
    if str(doc.fm.get("status") or "") not in _PLAN_STATUSES:
        return
    feat = doc.spec_id
    if not ids.matches_type("feature", feat):
        return
    try:
        report = task_validation.planning(ctx.base, feat)
    except workspace.WorkspaceError as exc:
        emit("L-082", str(exc), 1, feat)
        return
    for line in report["findings"]:
        emit("L-082", line, 1, feat)
    plan = paths.plan_file(ctx.base, feat)
    if plan.is_file():
        for line in task_validation.plan_findings(ctx.base, feat):
            emit("L-082", line, 1, feat)


def _epic(doc, ctx, emit) -> None:
    if doc.fm.get("status") not in {"draft", "approved"}:
        return
    done = doc.text("Done when").strip()
    scope = doc.text("Scope").strip()
    if not done or done == _PLACEHOLDER or "<" in done:
        emit(
            "L-081",
            "Done when needs a measurable exit criterion",
            doc.line("Done when") or 1,
            doc.spec_id,
        )
    if (
        not scope
        or scope == _PLACEHOLDER
        or "<" in scope
        or not re.search(r"in scope", scope, re.I)
        or not re.search(r"out of scope", scope, re.I)
    ):
        emit(
            "L-081",
            "Scope needs an in-scope list and an out-of-scope list",
            doc.line("Scope") or 1,
            doc.spec_id,
        )
    from kitlib import epics

    rows = {row["id"]: row for row in epics.feature_rows(doc.body)}
    members = {}
    for other in ctx.docs:
        if other.fm.get("type") != "feature" or other.card or not other.spec_id:
            continue
        epic = other.fm.get("epic")
        values = epic if isinstance(epic, list) else [epic]
        if any(str(item).split(":")[-1] == doc.spec_id for item in values if item):
            members[other.spec_id] = other.fm
    if set(rows) != set(members):
        emit(
            "L-081",
            "Features table does not list this epic's stories",
            doc.line("Features") or 1,
            doc.spec_id,
        )
        return
    for feat, fm in members.items():
        row = rows[feat]
        deps = sorted(str(item).split(":")[-1] for item in (fm.get("depends_on") or []))
        if (
            row["title"] != str(fm.get("title") or "")
            or row["priority"] != str(fm.get("priority") or "")
            or row["status"] != str(fm.get("status") or "")
            or row["depends_on"] != deps
        ):
            emit(
                "L-081",
                f"{feat} row disagrees with its front matter",
                doc.line("Features") or 1,
                feat,
            )


def _links(doc, ctx, emit) -> None:
    base = Path(ctx.base)
    source = (base / doc.path).parent
    for match in re.finditer(r"\[[^\]]*\]\(([^)\s]+)", doc.raw):
        href = match.group(1)
        if href.startswith(("#", "http://", "https://", "mailto:")):
            continue
        path = href.split("#", 1)[0]
        if not path.endswith(".md"):
            continue
        target = (source / path).resolve()
        try:
            target.relative_to(base.resolve())
        except ValueError:
            emit("L-072", f"link leaves the project: {href}", 1, doc.spec_id)
            continue
        if not target.is_file():
            emit("L-072", f"link does not resolve: {href}", 1, doc.spec_id)


def _clause(text: str, word: str) -> str:
    match = re.search(rf"(?im)^\s*-?\s*\*\*{word}\*\*\s*(.+)$", text)
    if match:
        return match.group(1).strip()
    match = re.search(rf"(?im)^\s*{word}\s+(.+)$", text)
    return match.group(1).strip() if match else ""


def _prefixed(text: str, prefix: str) -> set[str]:
    return {ref.id for ref in ids.find_refs(text) if ref.id.startswith(prefix)}


def _listed(value, prefix: str) -> set[str]:
    values = value if isinstance(value, list) else []
    return {
        str(item).split(":")[-1] for item in values if str(item).split(":")[-1].startswith(prefix)
    }


def _coverage_path(base: Path, feat: str) -> Path:
    return paths.feature_dir(base, feat) / f"{feat}.coverage.json"


def _load_coverage(base: Path, feat: str) -> dict | None:
    if not ids.matches_type("feature", feat):
        return None
    path = _coverage_path(base, feat)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _line_of(text: str, offset: int) -> int:
    return text[:offset].count("\n") + 1
