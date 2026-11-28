"""Turn a heading-feature catalogue snapshot into story text.

The compiler copies clauses that are already in the source. A missing Given, When, Then,
example, or observable result becomes an open question. It does not invent a sentence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kitlib import cite, frontmatter, hashing, ids, links, paths, schema

PROFILE = "heading-feature"
FEATURE = re.compile(r"^### (F\d{2}\.\d{2}) (.+)$")
_LABEL = re.compile(r"^\*\*(.+?)\*\*:?\s*(.*)$")
_PRIORITY = {"must": "must", "should": "should", "could": "could"}
_RANK = {"must": 0, "should": 1, "could": 2}
_BLOCKS = {
    "user story": "story",
    "what it does": "does",
    "business rules": "rules",
    "empty, loading and error states": "edge",
    "acceptance criteria": "ac",
    "mockup": "mockup",
}


@dataclass
class Item:
    legacy_id: str
    start: int
    end: int
    text: str
    block: str

    def sha(self, lines: list[str]) -> str:
        return cite.quote_hash(lines[self.start - 1 : self.end])

    def citation(self, src: str, lines: list[str]) -> str:
        span = f"L{self.start}" if self.end == self.start else f"L{self.start}-L{self.end}"
        return f"{src}:{span}#{self.sha(lines)}"


@dataclass
class Feature:
    legacy_id: str
    title: str
    start: int
    end: int
    priority: str = "should"
    release: str = ""
    needs: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)

    def item(self, block: str) -> list[Item]:
        return [item for item in self.items if item.block == block]

    @property
    def actor(self) -> str:
        return _persona(self)[0]

    @property
    def page(self) -> str:
        mock = self.item("mockup")
        return _page(mock[0].text) if mock else ""


@dataclass
class Catalogue:
    source: str
    lines: list[str]
    features: list[Feature]
    outside: list[Item] = field(default_factory=list)


@dataclass
class Gap:
    id: str
    title: str
    why: str
    citation: str
    quote: str


@dataclass
class Compiled:
    fm: dict[str, Any]
    body: str
    coverage: dict[str, Any]
    questions: list[Gap]
    rules: list[dict[str, str]]


def parse_snapshot(text: str, source: str) -> Catalogue:
    """Parse one snapshot. Raise ValueError when it has no `### Fxx.yy` features."""
    lines = text.splitlines()
    heads = [
        (i, m.group(1), m.group(2).strip())
        for i, line in enumerate(lines)
        if (m := FEATURE.match(line))
    ]
    if not heads:
        raise ValueError("snapshot does not match the heading-feature profile")
    features = []
    for index, (start, legacy, title) in enumerate(heads):
        end = heads[index + 1][0] if index + 1 < len(heads) else len(lines)
        for cursor in range(start + 1, end):
            if lines[cursor].startswith("## "):
                end = cursor
                break
        features.append(_feature(lines, start, end, legacy, title))
    return Catalogue(source, lines, features, _outside(lines, heads[0][0]))


def propose(text: str, source: str) -> dict[str, Any]:
    """Bundle features that share a legacy epic, actor and mockup page. Do not write stories."""
    catalogue = parse_snapshot(text, source)
    groups: dict[tuple[str, str, str], list[Feature]] = {}
    for feature in catalogue.features:
        key = (feature.legacy_id.split(".")[0], feature.actor.casefold(), feature.page.casefold())
        groups.setdefault(key, []).append(feature)
    bundles = []
    for features in groups.values():
        current: list[Feature] = []
        count = 0
        for feature in features:
            acs = len(feature.item("ac"))
            if current and count + acs > 7:
                bundles.append(_bundle(current))
                current, count = [], 0
            current.append(feature)
            count += acs
        if current:
            bundles.append(_bundle(current))
    return {"profile": PROFILE, "source": source, "bundles": bundles}


def proposal_items(payload: dict[str, Any]) -> list[str]:
    """`Title|F04.06,F04.07` rows for accept-split."""
    items = []
    for bundle in payload.get("bundles") or []:
        title = str(bundle.get("title") or "").strip()
        aliases = ",".join(str(item) for item in bundle.get("legacy_ids") or [])
        items.append(f"{title}|{aliases}" if aliases else title)
    return items


def render(
    catalogue: Catalogue,
    features: list[Feature],
    feat: str,
    scope: str,
    bo: str,
    taken: list[str],
    dep_map: dict[str, str] | None = None,
    epic: str | None = None,
    base: Path | None = None,
    story_path: Path | None = None,
) -> Compiled:
    """Story body, coverage and the questions a writer still has to open."""
    if not features:
        raise ValueError("compile needs at least one source feature")
    if not bo or not ids.matches_type("bo", bo.split(":")[-1]):
        raise ValueError("compile needs a business objective such as BO-001")
    number = ids.feat_number(feat)
    dep_map = dep_map or {}
    lines = catalogue.lines
    questions: list[Gap] = []
    rules: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    ac_no = 0

    def alloc(prefix: str) -> str:
        identity = ids.next_id(prefix, taken)
        taken.append(identity)
        return identity

    def gap(title: str, why: str, item: Item) -> str:
        identity = alloc("Q")
        questions.append(
            Gap(identity, _fit(title, 120), why, item.citation(catalogue.source, lines), item.text)
        )
        return identity

    goal_bits = []
    context = []
    ac_blocks = []
    rule_lines = []
    edge_lines = []
    ui_lines = []
    out_lines = []
    dep_lines = []
    br_ids: list[str] = []
    depends: list[str] = []
    actors = {feature.actor for feature in features if feature.actor}
    if len(actors) > 1:
        raise ValueError("a story bundles one actor; split the source features first")
    actor = next(iter(actors), "")
    wants, outcomes = [], []

    for feature in features:
        story = feature.item("story")
        if story:
            sentence = story[0].text
            who, want, outcome = _split_story(sentence)
            if who:
                wants.append(want)
                outcomes.append(outcome)
            goal_bits.append(story[0].citation(catalogue.source, lines))
            context.append(f"{sentence} ({story[0].citation(catalogue.source, lines)})")
            rows.append(_row(catalogue, feature.legacy_id, story[0], "context", ""))
        elif feature.actor == "":
            pass
        ac_text = []
        prepared = []
        for item in feature.item("ac"):
            given, when, then = _gwt(_ac_sentence(item.text))
            prepared.append((item, given, when, then))
            ac_text.append(" ".join(part for part in (given, when, then) if part))
        for item in feature.item("does"):
            sentence = _bullet(item.text)
            if re.search(r"\bGiven\b.+\bThen\b", sentence, re.I):
                given, when, then = _gwt(sentence)
                ac_no += 1
                ac_id = ids.ac_id(number, ac_no)
                block, qid = _ac_block(ac_id, given, when, then, item, catalogue, lines, gap, ac_no)
                ac_blocks.append(block)
                rows.append(_row(catalogue, feature.legacy_id, item, "ac", ac_id, qid))
                continue
            if _covered(sentence, ac_text):
                context.append(f"{sentence} ({item.citation(catalogue.source, lines)})")
                rows.append(_row(catalogue, feature.legacy_id, item, "context", ""))
            else:
                qid = gap(
                    f"Which result proves: {sentence}",
                    "No acceptance criterion states this behaviour.",
                    item,
                )
                context.append(
                    f"{sentence} ({item.citation(catalogue.source, lines)}) unanswered ({qid})"
                )
                rows.append(_row(catalogue, feature.legacy_id, item, "q", qid, qid))
        for item in feature.item("rules"):
            sentence = _br_sentence(item.text)
            br_id = alloc("BR")
            br_ids.append(br_id)
            qid = ""
            if re.search(r"\bExample:\s*\S", sentence, re.I):
                example = ""
            else:
                qid = gap(
                    f"Worked example for {br_id}",
                    "The source rule has no worked example.",
                    item,
                )
                example = f" Example: unanswered ({qid})."
            rule_lines.append(
                f"- {br_id}: {sentence}{example} ({item.citation(catalogue.source, lines)})"
            )
            rules.append(
                {
                    "id": br_id,
                    "title": _fit(sentence, 120),
                    "citation": item.citation(catalogue.source, lines),
                    "question": qid,
                    "text": sentence,
                }
            )
            rows.append(_row(catalogue, feature.legacy_id, item, "br", br_id, qid))
        for item in feature.item("edge"):
            edge_lines.append(f"- {_bullet(item.text)} ({item.citation(catalogue.source, lines)})")
            rows.append(_row(catalogue, feature.legacy_id, item, "edge", ""))
        for item, given, when, then in prepared:
            ac_no += 1
            ac_id = ids.ac_id(number, ac_no)
            block, qid = _ac_block(ac_id, given, when, then, item, catalogue, lines, gap, ac_no)
            ac_blocks.append(block)
            rows.append(_row(catalogue, feature.legacy_id, item, "ac", ac_id, qid))
        for item in feature.item("mockup"):
            qid = gap(
                f"Which asset shows {_page(item.text) or feature.legacy_id}",
                "The source names a mockup and no asset is registered for it.",
                item,
            )
            ui_lines.append(f"{item.text} ({item.citation(catalogue.source, lines)})")
            ui_lines.append(
                "The source does not name the default, empty, loading or error copy. "
                f"unanswered ({qid})."
            )
            rows.append(_row(catalogue, feature.legacy_id, item, "ui", qid, qid))
        for need in feature.needs:
            owner = dep_map.get(need)
            if owner and owner not in depends:
                depends.append(owner)
                linked = (
                    links.link_for(owner, story_path, base)
                    if base is not None and story_path
                    else None
                )
                dep_lines.append(linked or owner)
            elif not owner:
                probe = feature.item("story") or feature.items[:1]
                if not probe:
                    continue
                qid = gap(
                    f"Which feature supplies {need}",
                    "The source Needs link is not an alias of a reserved feature.",
                    probe[0],
                )
                dep_lines.append(f"{need} is not a reserved feature. unanswered ({qid}).")

    legacy = [feature.legacy_id for feature in features]
    span = _span_cite(catalogue, features)
    if actor and wants:
        goal = (
            f"As {actor}, I want {' and '.join(dict.fromkeys(wants))}, so that "
            f"{' and '.join(dict.fromkeys(outcomes))}. Business objective: {bo.split(':')[-1]}."
        )
    else:
        qid = questions[0].id if questions else ""
        goal = f"Business objective: {bo.split(':')[-1]}."
        if not qid and features[0].items:
            qid = gap(
                "Who is the actor", "The source user story could not be read.", features[0].items[0]
            )
            goal += f" unanswered ({qid})."
    if goal_bits:
        goal += " (" + "; ".join(goal_bits) + ")"

    named = ", ".join(legacy)
    if not edge_lines:
        edge_lines.append(f"None — {named} has no empty, loading or error states ({span}).")
    ui = "\n\n".join(ui_lines) if ui_lines else f"None — {named} has no mockup line ({span})."
    matched = [item for item in catalogue.outside if any(fid in item.text for fid in legacy)]
    if matched:
        for item in matched:
            out_lines.append(
                f"- {item.text} — reason: named by the source scope "
                f"({item.citation(catalogue.source, lines)})."
            )
            rows.append(_row(catalogue, legacy[0], item, "out", ""))
    else:
        out_lines.append(f"None — no out-of-scope line names {named} ({span}).")
    if not dep_lines:
        dep_lines.append(f"None — {named} names no unmet need ({span}).")
    else:
        dep_lines = [f"- {line}" if not line.startswith("- ") else line for line in dep_lines]
    if questions:
        open_q = "\n".join(f"- {q.id} {q.title} ({q.citation})" for q in questions)
    else:
        open_q = f"None — coverage map records no gap ({span})."

    sections = {
        "Goal": goal,
        "Context": "\n".join(f"- {line}" if not line.startswith("- ") else line for line in context)
        or f"None — no context lines ({span}).",
        "Acceptance criteria": "\n".join(ac_blocks).strip(),
        "Business rules": "\n".join(rule_lines)
        if rule_lines
        else f"None — {named} states no business rule ({span}).",
        "Edge cases and error behavior": "\n".join(edge_lines),
        "Non-functional": f"None — {named} states no quality target ({span}).",
        "UI/UX": ui,
        "Out of scope": "\n".join(out_lines),
        "Dependencies and relations": "\n".join(dep_lines),
        "Open questions": open_q,
    }
    body = "".join(f"## {name}\n\n{sections[name].strip()}\n\n" for name in schema.STORY_SECTIONS)
    priority = min((feature.priority for feature in features), key=lambda item: _RANK.get(item, 9))
    releases = [feature.release for feature in features if feature.release]
    fm: dict[str, Any] = {
        "id": feat,
        "type": "feature",
        "scope": scope,
        "title": _fit("; ".join(feature.title for feature in features), 100),
        "aliases": list(legacy),
        "legacy_ids": list(legacy),
        "status": "draft",
        "priority": priority,
        "release": _release(releases),
        "epic": epic.split(":")[-1] if epic else None,
        "bo": [bo.split(":")[-1]],
        "br": br_ids,
        "nfr": [],
        "sources": [catalogue.source],
        "assets": [],
        "links": [],
        "depends_on": depends,
        "code": True,
        "jira_key": None,
    }
    coverage = {
        "profile": PROFILE,
        "source": catalogue.source,
        "legacy_ids": list(legacy),
        "actor": actor,
        "page": features[0].page if len({feature.page for feature in features}) == 1 else "",
        "sizing_dec": None,
        "items": rows,
    }
    text = hashing.stamp(frontmatter.render(fm, body))
    fm = frontmatter.parse(text).fm or fm
    return Compiled(fm, frontmatter.parse(text).body, coverage, questions, rules)


def coverage_problems(snapshot: str, source: str, coverage: dict[str, Any]) -> list[str]:
    """Re-parse the cited spans and report items the coverage map dropped or rewrote."""
    if coverage.get("profile") != PROFILE or coverage.get("source") != source:
        return ["coverage file is not a heading-feature map for this snapshot"]
    try:
        catalogue = parse_snapshot(snapshot, source)
    except ValueError as exc:
        return [str(exc)]
    wanted = set(coverage.get("legacy_ids") or [])
    items = [
        item
        for feature in catalogue.features
        if feature.legacy_id in wanted
        for item in feature.items
    ]
    mapped = {
        (row.get("legacy_id"), row.get("start"), row.get("end")): row
        for row in coverage.get("items") or []
    }
    problems = []
    for item in items:
        row = mapped.get((item.legacy_id, item.start, item.end))
        if row is None:
            problems.append(f"no disposition for {item.legacy_id} L{item.start}")
        elif row.get("sha") != item.sha(catalogue.lines):
            problems.append(f"hash mismatch for {item.legacy_id} L{item.start}")
    return problems


def write_reserved(
    root: Path,
    scope: str,
    source_id: str,
    legacy_ids: list[str],
    feat: str,
    bo: str,
    epic: str | None = None,
    dry_run: bool = False,
) -> Path:
    """Write the story, coverage, rule cards and questions for one reserved feature."""
    from kitlib import fsio, recordops, workspace

    base = workspace.scope_dir(root, scope)
    path = ids.find_record(base / "sources", source_id)
    if path is None:
        raise ValueError(f"no snapshot {source_id}")
    catalogue = parse_snapshot(path.read_text(encoding="utf-8"), source_id)
    by_id = {feature.legacy_id: feature for feature in catalogue.features}
    missing = [item for item in legacy_ids if item not in by_id]
    if missing:
        raise ValueError(f"not in {source_id}: {', '.join(missing)}")
    target = paths.story(base, feat)
    if target.exists():
        raise ValueError(f"{feat} already has a story")
    taken = ids.taken_ids(base)
    compiled = render(
        catalogue,
        [by_id[item] for item in legacy_ids],
        feat,
        scope,
        bo,
        taken,
        _alias_map(base, scope),
        epic,
        base,
        target,
    )
    story = hashing.stamp(frontmatter.render(compiled.fm, compiled.body))
    if dry_run:
        print(json.dumps({"story": str(target), "questions": [q.id for q in compiled.questions]}))
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    fsio.atomic_write(target, story)
    fsio.atomic_write(
        target.with_name(f"{feat}.coverage.json"),
        json.dumps(compiled.coverage, indent=1) + "\n",
    )
    for rule in compiled.rules:
        _write_rule(base, scope, rule)
    if compiled.questions:
        ctx = recordops.Ctx(root, scope, "sw-craft")
        plan = recordops.new_plan(ctx)
        for question in compiled.questions:
            plan = recordops.question_new(
                ctx,
                question.title,
                [feat],
                "compiler",
                why=question.why,
                raised_from=[question.citation],
                quote=question.quote,
                status="open",
                identity=question.id,
                plan=plan,
            )
        recordops.execute(ctx, plan, "compile-questions", f"{scope}:{feat}")
    return target


def _write_rule(base: Path, scope: str, rule: dict[str, str]) -> None:
    from kitlib import fsio

    example = f"unanswered ({rule['question']})." if rule.get("question") else "see the story."
    fm = {
        "id": rule["id"],
        "type": "br",
        "scope": scope,
        "title": rule["title"],
        "aliases": [],
        "status": "draft",
    }
    body = f"{rule['text']}\n\nExample: {example}\n\n{rule['citation']}\n"
    path = base / "analysis" / ids.record_filename(rule["id"], rule["title"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        fsio.atomic_write(path, frontmatter.render(fm, body))


def _alias_map(base: Path, scope: str) -> dict[str, str]:
    from kitlib import rtm, schema

    registry = base / ".metadata/id-registry.md"
    if not registry.is_file():
        return {}
    try:
        table = rtm.read_table(registry, list(schema.REGISTRY_COLUMNS)).table
    except (OSError, ValueError):
        return {}
    found: dict[str, str] = {}
    for row in table.rows:
        if table.value(row[0], "State") in ("withdrawn", "superseded"):
            continue
        if row[0].split(":")[0] != scope:
            continue
        feat = row[0].split(":")[-1]
        if not ids.matches_type("feature", feat):
            continue
        for alias in table.value(row[0], "Aliases").split("|"):
            if alias.strip():
                found.setdefault(alias.strip(), feat)
    return found


def _feature(lines: list[str], start: int, end: int, legacy: str, title: str) -> Feature:
    feature = Feature(legacy, title, start + 1, end)
    block = ""
    for number in range(start + 1, end):
        line = lines[number]
        if not line.strip():
            continue
        meta = _meta(line)
        if meta:
            feature.priority, feature.release, feature.needs = meta
            continue
        label, rest = _label(line)
        if label:
            block = label
            if label == "story" and rest:
                feature.items.append(Item(legacy, number + 1, number + 1, rest, "story"))
            elif label == "mockup" and rest:
                feature.items.append(Item(legacy, number + 1, number + 1, rest, "mockup"))
            continue
        if block in {"does", "rules", "edge", "ac"} and re.match(r"^\s*-\s+", line):
            feature.items.append(Item(legacy, number + 1, number + 1, line.strip(), block))
    return feature


def _outside(lines: list[str], stop: int) -> list[Item]:
    found = []
    active = False
    for number, line in enumerate(lines[:stop]):
        if line.startswith("## "):
            active = False
        if line.strip() in {"**Out of scope**", "**Out of scope.**"}:
            active = True
            continue
        if active and line.startswith("**"):
            active = False
        if active and line.startswith("- "):
            found.append(Item("", number + 1, number + 1, _bullet(line), "out"))
    return found


def _meta(line: str) -> tuple[str, str, list[str]] | None:
    priority = re.search(r"\*\*Priority:\*\*\s*([A-Za-z]+)", line) or re.search(
        r"\*\*Priority\*\*:\s*([A-Za-z]+)", line
    )
    if not priority:
        return None
    release = re.search(r"\*\*Release:\*\*\s*(\S+)", line) or re.search(
        r"\*\*Release\*\*:\s*(\S+)", line
    )
    word = priority.group(1).casefold()
    return (
        _PRIORITY.get(word, "should"),
        (release.group(1).strip("·") if release else ""),
        re.findall(r"F\d{2}\.\d{2}", line.split("**Needs:**")[-1] if "Needs" in line else ""),
    )


def _label(line: str) -> tuple[str, str]:
    match = _LABEL.match(line.strip())
    if not match:
        return "", ""
    name = match.group(1).strip().rstrip(".:").casefold()
    return _BLOCKS.get(name, ""), match.group(2).strip()


def _bullet(line: str) -> str:
    return re.sub(r"^\s*-\s*", "", line).strip()


def _ac_sentence(line: str) -> str:
    text = re.sub(r"^\s*-\s*\[[ xX]\]\s*", "", line)
    return re.sub(r"^\*\*AC\d+\.\*\*\s*", "", text).strip()


def _br_sentence(line: str) -> str:
    text = re.sub(r"^\s*-\s*", "", line)
    return re.sub(r"^\*\*BR\d+\.\*\*\s*", "", text).strip()


def _gwt(sentence: str) -> tuple[str, str, str]:
    then = when = given = ""
    match = re.search(r"\bthen\b\s+(.*)$", sentence, re.I)
    if match:
        then = match.group(1).strip().rstrip(".")
        sentence = sentence[: match.start()]
    match = re.search(r"\bwhen\b\s+(.*)$", sentence, re.I)
    if match:
        when = match.group(1).strip().rstrip(",").strip()
        sentence = sentence[: match.start()]
    match = re.search(r"\bgiven\b\s+(.*)$", sentence, re.I)
    if match:
        given = match.group(1).strip().rstrip(",").strip()
    return given, when, then


def _split_story(sentence: str) -> tuple[str, str, str]:
    match = re.match(r"As (an? .+?), I want (.+?), so that (.+?)\.?$", sentence.strip(), re.I)
    if not match:
        return "", "", ""
    return match.group(1).strip(), match.group(2).strip(), match.group(3).strip().rstrip(".")


def _persona(feature: Feature) -> tuple[str, str, str]:
    story = feature.item("story")
    return _split_story(story[0].text) if story else ("", "", "")


def _page(mockup: str) -> str:
    text = re.split(r"\bActions:", mockup, maxsplit=1)[0]
    return text.split(",")[0].split(".")[0].strip().strip("`")


def _covered(sentence: str, ac_text: list[str]) -> bool:
    words = {word for word in re.findall(r"[A-Za-z0-9']{4,}", sentence.casefold())}
    blob = " ".join(ac_text).casefold()
    hits = sum(1 for word in words if re.search(rf"\b{re.escape(word)}\b", blob))
    return bool(words) and hits >= 4 and hits * 2 >= len(words)


def _observable(text: str) -> bool:
    return bool(re.search(r'\d|"[^"\n]+"|“[^”\n]+”|\'[^\'\n]+\'', text or ""))


def _ac_block(ac_id, given, when, then, item, catalogue, lines, gap, ac_no):
    qids = []
    if not given:
        qids.append(gap(f"What is given for {ac_id}", "The source criterion has no Given.", item))
        given = f"unanswered ({qids[-1]})"
    if not when:
        qids.append(gap(f"What starts {ac_id}", "The source criterion has no When.", item))
        when = f"unanswered ({qids[-1]})"
    if not then:
        qids.append(
            gap(f"What is the result of {ac_id}", "The source criterion has no Then.", item)
        )
        then = f"unanswered ({qids[-1]})"
    elif not _observable(then):
        qids.append(
            gap(
                f"Which observable proves {ac_id}",
                "The source Then has no number or quoted result.",
                item,
            )
        )
        then = f"{then}. unanswered ({qids[-1]})"
    citation = item.citation(catalogue.source, lines)
    title = _fit(then.replace("unanswered", "").strip(" ."), 80) or f"criterion {ac_no}"
    block = (
        f"### {ac_id} — {title}\n\n"
        f"- **Given** {given}\n- **When** {when}\n- **Then** {then}\n\n{citation}\n"
    )
    return block, qids[0] if qids else ""


def _row(catalogue, legacy, item: Item, disposition: str, target: str, question: str = "") -> dict:
    row = {
        "src": catalogue.source,
        "legacy_id": legacy or item.legacy_id,
        "start": item.start,
        "end": item.end,
        "sha": item.sha(catalogue.lines),
        "text": item.text,
        "disposition": disposition,
        "target": target,
    }
    if question:
        row["question"] = question
    return row


def _span_cite(catalogue: Catalogue, features: list[Feature]) -> str:
    start = min(feature.start for feature in features)
    end = max(feature.end for feature in features)
    digest = cite.quote_hash(catalogue.lines[start - 1 : end])
    span = f"L{start}" if start == end else f"L{start}-L{end}"
    return f"{catalogue.source}:{span}#{digest}"


def _bundle(features: list[Feature]) -> dict[str, Any]:
    releases = [feature.release for feature in features if feature.release]
    priority = min((feature.priority for feature in features), key=lambda item: _RANK.get(item, 9))
    return {
        "title": _fit("; ".join(feature.title for feature in features), 100),
        "legacy_ids": [feature.legacy_id for feature in features],
        "actor": features[0].actor,
        "page": features[0].page if len({feature.page for feature in features}) == 1 else "",
        "ac_count": sum(len(feature.item("ac")) for feature in features),
        "priority": priority,
        "release": _release(releases),
    }


def _release(releases: list[str]) -> str:
    if not releases:
        return ""

    def key(value: str) -> int:
        match = re.search(r"\d+", value)
        return int(match.group()) if match else 0

    return max(releases, key=key)


def _fit(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut or text[:limit]
