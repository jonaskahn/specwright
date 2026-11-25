"""Decide whether a feature needs a picture, from the story text and diagram citations.

The counter is deterministic: it never calls a model and never invents an actor, a state or an
ID. The word lists are the ones the sw-spec illustration note publishes, so the two stay aligned.
A dismissal lives in front matter, which the draft hash ignores, so recording one does not
touch approval. Diagram paths are not stored; citations come from a fresh graph's illustrates
edges, or from diagrams/*.json through the same spec-id walk the graph uses.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from kitlib import frontmatter, fsio, graph, graph_query, ids, markdown, workspace

DRAW = "DRAW"
PROSE = "PROSE"
UNSURE = "UNSURE"
ILLUSTRATED = "illustrated"
NEEDS = "needs illustration"
NONE = "no illustration"
CHECK = "check illustration"
CHIPS = (ILLUSTRATED, NEEDS, NONE, CHECK)

# Optional trailing "s" so "customers" counts as customer. Hyphenated words stay out.
ROLES = (
    "administrator",
    "subscriber",
    "supervisor",
    "moderator",
    "requester",
    "approver",
    "reviewer",
    "merchant",
    "operator",
    "assignee",
    "employee",
    "customer",
    "shopper",
    "auditor",
    "analyst",
    "cashier",
    "manager",
    "visitor",
    "seller",
    "member",
    "vendor",
    "client",
    "teller",
    "staff",
    "buyer",
    "agent",
    "guest",
    "owner",
    "payer",
    "admin",
    "clerk",
    "actor",
    "user",
)
_ROLE_SET = frozenset(ROLES)
BRANCH_WORDS = ("unless", "otherwise", "except", "only", "else", "not", "or", "if")
STATE_VERBS = (
    "unassigned",
    "deactivated",
    "transferred",
    "registered",
    "withdrawn",
    "suspended",
    "cancelled",
    "activated",
    "unblocked",
    "published",
    "completed",
    "refunded",
    "reversed",
    "archived",
    "rejected",
    "approved",
    "recorded",
    "restored",
    "assigned",
    "canceled",
    "expired",
    "deleted",
    "removed",
    "created",
    "revoked",
    "blocked",
    "changed",
    "cleared",
    "updated",
    "unlocked",
    "voided",
    "issued",
    "joined",
    "failed",
    "locked",
    "opened",
    "closed",
    "added",
    "left",
)
DATA_WORDS = (
    "notifications",
    "notification",
    "payloads",
    "receives",
    "received",
    "notifies",
    "notified",
    "payload",
    "receive",
    "notify",
    "sends",
    "sent",
    "send",
)
_BEHAVIOUR = (
    "Goal",
    "Context",
    "Acceptance criteria",
    "Business rules",
    "Edge cases and error behavior",
    "UI/UX",
    "Dependencies and relations",
)
_ACTOR_SECTIONS = ("Goal", "Business rules")
_HANDOFF_SECTIONS = ("Context", "Dependencies and relations")
_DATA_SECTIONS = _BEHAVIOUR
_DOC_FOLDERS = ("01-analysis", "02-drafts", "records")
_STALE_RESOLUTION = {"withdrawn", "unresolved"}

# Longer forms first so "customers" is the customer role, not a truncated stem.
_ROLE = re.compile(
    r"(?<![\w-])(?:"
    + "|".join(sorted({*ROLES, *(role + "s" for role in ROLES)}, key=len, reverse=True))
    + r")(?![\w-])",
    re.I,
)
_BRANCH = re.compile(r"(?<![\w-])(?:" + "|".join(BRANCH_WORDS) + r")(?![\w-])", re.I)
_STATE = re.compile(r"(?<![\w-])(?:" + "|".join(STATE_VERBS) + r")(?![\w-])", re.I)
_DATA = re.compile(r"(?<![\w-])(?:" + "|".join(DATA_WORDS) + r")(?![\w-])", re.I)
_STATUS = re.compile(r"(?i)\bstatus\s+(?:is\s+)?[\"“][^\"”\n]+[\"”]")
_FEAT = re.compile(r"\b(?:[A-Z]{2,5}:)?(FEAT-\d{3})\b")
_NONE = re.compile(r"(?i)^none\b")
_QUOTE = re.compile(r"[\"“][^\"”\n]+[\"”]")
_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Signals:
    actors: int
    branches: int
    state_changes: int
    handoffs: int
    data_moves: int

    @property
    def items(self) -> int:
        return self.actors + self.branches + self.state_changes + self.handoffs + self.data_moves

    def fired(self) -> tuple[str, ...]:
        """Signal names that cleared their threshold. Two or more is the draw line."""
        names = []
        if self.actors >= 2:
            names.append("actors")
        if self.branches >= 1:
            names.append("branches")
        if self.state_changes >= 1:
            names.append("state_changes")
        if self.handoffs >= 1:
            names.append("handoffs")
        if self.data_moves >= 1:
            names.append("data_moves")
        return tuple(names)

    def as_dict(self) -> dict[str, Any]:
        return {
            "actors": self.actors,
            "branches": self.branches,
            "state_changes": self.state_changes,
            "handoffs": self.handoffs,
            "data_moves": self.data_moves,
            "items": self.items,
            "fired": list(self.fired()),
        }


def _roles_in(text: str) -> set[str]:
    found = set()
    for match in _ROLE.finditer(text):
        word = match.group(0).casefold()
        if word not in _ROLE_SET and word.endswith("s") and word[:-1] in _ROLE_SET:
            word = word[:-1]
        if word in _ROLE_SET:
            found.add(word)
    return found


def _unfenced(lines: list[tuple[int, str]]) -> list[str]:
    kept: list[str] = []
    fenced = False
    for _, line in lines:
        if _FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            kept.append(line)
    return kept


def _section_lines(sections: dict[str, markdown.Section], name: str) -> list[str]:
    section = sections.get(name)
    return _unfenced(section.lines) if section else []


def _section_text(sections: dict[str, markdown.Section], names: tuple[str, ...]) -> str:
    return "\n".join(
        line for name in names for line in _section_lines(sections, name) if line.strip()
    )


def _clause(line: str, word: str) -> bool:
    return bool(re.match(rf"(?i)^\s*(?:[-*+]\s+)?(?:\*\*|__)?{word}\b", line))


def _branchy(text: str) -> bool:
    return bool(_BRANCH.search(text) or _roles_in(text))


def _edge_error(line: str) -> bool:
    stripped = re.sub(r"^\s*[-*]\s+", "", line).strip()
    if not stripped or _NONE.match(stripped):
        return False
    bullet = bool(re.match(r"\s*[-*]\s+\S", line))
    conditional = bool(re.match(r"(?i)\s*(?:[-*]\s+)?if\b", line))
    return bullet or conditional or bool(_QUOTE.search(line))


def _state_line(line: str) -> bool:
    return bool(_STATE.search(line) or _STATUS.search(line))


def _handoff_count(text: str, own: str, aliases: tuple[str, ...]) -> int:
    found = {match.group(1) for match in _FEAT.finditer(text) if match.group(1) != own}
    for alias in aliases:
        if len(alias.strip()) < 3 or alias.strip().casefold() == own.casefold():
            continue
        if re.search(rf"(?i)(?<![\w-]){re.escape(alias.strip())}(?![\w-])", text):
            found.add(alias.strip().casefold())
    return len(found)


def count_signals(story: str, aliases: tuple[str, ...] | None = None) -> Signals:
    """Count the five signals from one story. Aliases are other features' names, if known."""
    parsed = frontmatter.parse(story)
    if parsed.error:
        raise ValueError(parsed.error)
    fm = parsed.fm or {}
    own = str(fm.get("id") or "")
    sections = markdown.sections(parsed.body)
    ac_lines = _section_lines(sections, "Acceptance criteria")
    actor_lines = [line for line in ac_lines if _clause(line, "Given") or _clause(line, "When")]
    actors = _roles_in(_section_text(sections, _ACTOR_SECTIONS) + "\n" + "\n".join(actor_lines))
    titles = [
        block.title
        for block in markdown.ac_blocks(sections.get("Acceptance criteria")).values()
        if block.title
    ]
    rule_rows = [line for line in _section_lines(sections, "Business rules") if line.strip()]
    edge_rows = [
        line
        for line in _section_lines(sections, "Edge cases and error behavior")
        if _edge_error(line)
    ]
    branches = [text for text in (*titles, *rule_rows) if _branchy(text)]
    states = [line for line in ac_lines if _clause(line, "Then") and _state_line(line)]
    handoffs = _handoff_count(_section_text(sections, _HANDOFF_SECTIONS), own, aliases or ())
    data_lines = [
        line for line in _section_text(sections, _DATA_SECTIONS).splitlines() if _DATA.search(line)
    ]
    return Signals(
        len(actors),
        len(branches) + len(edge_rows),
        len(states),
        handoffs,
        len(data_lines),
    )


def verdict(signals: Signals) -> str:
    """DRAW at two signals once the picture is large enough; prose for one actor and a short list.

    The borderline band is UNSURE: exactly two signals with fewer than five items, or several
    actors and no other signal. One actor and fewer than five items stays prose even when two
    signals fired, which is the kit's paragraph rule.
    """
    fired = len(signals.fired())
    if signals.actors <= 1 and signals.items < 5:
        return PROSE
    if fired >= 3 or (fired >= 2 and signals.items >= 5):
        return DRAW
    if fired == 2 or (fired == 1 and signals.actors >= 2):
        return UNSURE
    return PROSE


def _bare(feature: str) -> str:
    ref = ids.parse_ref(feature.strip())
    feat = ref.id if ref else feature.strip()
    if not ids.matches_type("feature", feat):
        raise ValueError(f"{feature} is not a feature ID such as FEAT-002")
    return feat


def _story_path(base: Path, feat: str) -> Path:
    path = base / "02-drafts" / f"{feat}.story.md"
    if not path.is_file():
        raise ValueError(f"{path} does not exist")
    return path


def _belongs(qualified: str, scope: str, feat: str, number: int) -> bool:
    ref = ids.parse_ref(qualified)
    if ref is None:
        return False
    if (ref.scope or scope) != scope:
        return False
    if ref.id == feat:
        return True
    parsed = ids.parse_ac(ref.id)
    return parsed is not None and parsed[0] == number


def _ids_in(story: str, scope: str) -> tuple[set[str], set[str]]:
    """Live and withdrawn IDs this story itself defines."""
    parsed = frontmatter.parse(story)
    fm = parsed.fm or {}
    live: set[str] = set()
    withdrawn: set[str] = set()
    feat = str(fm.get("id") or "")
    if ids.matches_type("feature", feat):
        bucket = withdrawn if str(fm.get("status") or "") in {"withdrawn", "superseded"} else live
        bucket.add(ids.qualify(scope, feat))
    sections = markdown.sections(parsed.body)
    criteria = sections.get("Acceptance criteria")
    for acid in markdown.ac_blocks(criteria):
        live.add(ids.qualify(scope, acid))
    for acid in markdown.ac_tombstones(criteria):
        key = ids.qualify(scope, acid)
        live.discard(key)
        withdrawn.add(key)
    return live, withdrawn


def _scope_ids(base: Path, scope: str) -> tuple[set[str], set[str]]:
    live: set[str] = set()
    withdrawn: set[str] = set()
    for folder in _DOC_FOLDERS:
        root = base / folder
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if path.is_symlink() or "raw" in path.relative_to(base).parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            parsed = frontmatter.parse(text)
            if parsed.error or not parsed.fm:
                continue
            fm = parsed.fm
            spec_id = str(fm.get("id") or "")
            ref = ids.parse_ref(spec_id)
            if ref and not ref.scope:
                key = ids.qualify(scope, ref.id)
                if str(fm.get("status") or "") in {"withdrawn", "superseded"}:
                    withdrawn.add(key)
                else:
                    live.add(key)
            part_live, part_gone = _ids_in(text, scope)
            live |= part_live
            withdrawn |= part_gone
    live -= withdrawn
    return live, withdrawn


def _other_aliases(base: Path | None, feat: str) -> tuple[str, ...]:
    if base is None:
        return ()
    folder = base / "02-drafts"
    if not folder.is_dir():
        return ()
    found: list[str] = []
    for path in sorted(folder.glob("*.story.md")):
        if path.is_symlink():
            continue
        try:
            parsed = frontmatter.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError):
            continue
        fm = parsed.fm or {}
        if str(fm.get("id") or "") == feat:
            continue
        for alias in fm.get("aliases") or []:
            text = str(alias).strip()
            if len(text) >= 3:
                found.append(text)
    return tuple(dict.fromkeys(found))


def _fresh_edges(base: Path, scope: str) -> list[graph.Edge] | None:
    """Illustrates edges when the on-disk graph still matches its inputs."""
    try:
        root = workspace.find_root(base)
    except workspace.WorkspaceError:
        return None
    if root is None:
        return None
    try:
        store = graph_query.Store(root, scope)
    except (OSError, ValueError):
        return None
    if store.freshness() != "fresh":
        return None
    return [edge for edge in store.edges("out") if edge.rel == "illustrates"]


def _covering(
    edges_or_ids: list[tuple[str, str, str]], scope: str, feat: str, number: int
) -> tuple[bool, list[str]]:
    """(covers this feature, stale qualified ids). Each tuple is (diagram, target, resolution)."""
    diagrams = {src for src, dst, _res in edges_or_ids if _belongs(dst, scope, feat, number)}
    if not diagrams:
        return False, []
    stale = sorted(
        {dst for src, dst, res in edges_or_ids if src in diagrams and res in _STALE_RESOLUTION}
    )
    return True, stale


def _json_citations(
    base: Path, scope: str, live: set[str], withdrawn: set[str]
) -> list[tuple[str, str, str]]:
    folder = base / "diagrams"
    if not folder.is_dir():
        return []
    rows: list[tuple[str, str, str]] = []
    for path in sorted(folder.glob("*.json")):
        if path.is_symlink():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        # Same walk graph.build uses, so a picture the graph would link is a picture here.
        for target in graph._spec_ids(data, scope):  # noqa: SLF001
            if target in withdrawn:
                res = "withdrawn"
            elif target in live:
                res = "resolved"
            else:
                res = "unresolved"
            rows.append((path.name, target, res))
    return rows


def _citations(
    base: Path | None, scope: str, live: set[str], withdrawn: set[str]
) -> list[tuple[str, str, str]]:
    if base is None:
        return []
    edges = _fresh_edges(base, scope)
    if edges is not None:
        return [(edge.src, edge.dst, edge.res) for edge in edges]
    return _json_citations(base, scope, live, withdrawn)


_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
_EMBED_SECTIONS = ("Context", "UI/UX")


def embeds(story: str, base: Path) -> list[tuple[str, Path | None]]:
    """Local images the story shows in Context or UI/UX, as (written path, file or None).

    A path is read from the story's own folder, so `../diagrams/x.svg` is the picture
    `diagrams/x.svg` of the project. Remote and absolute targets are not local pictures.
    """
    parsed = frontmatter.parse(story)
    sections = markdown.sections(parsed.body)
    found: list[tuple[str, Path | None]] = []
    root = base.resolve()
    for name in _EMBED_SECTIONS:
        for line in _section_lines(sections, name):
            for match in _IMAGE.finditer(line):
                ref = match.group(1)
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:|^[/\\]", ref):
                    continue
                path = (base / "02-drafts" / ref.split("#", 1)[0]).resolve()
                found.append((ref, path if path.is_relative_to(root) and path.is_file() else None))
    return found


def pictures(
    story: str, base: Path | None, scope: str, feat: str, number: int
) -> tuple[list[dict[str, Any]], list[str]]:
    """The rendered pictures of this feature, and the embedded images that point nowhere.

    A picture is a `diagrams/*.svg` whose JSON sidecar cites the feature or one of its criteria.
    """
    if base is None or not (base / "diagrams").is_dir():
        return [], []
    shown = {path for _, path in embeds(story, base) if path is not None}
    rows: list[dict[str, Any]] = []
    for path in sorted((base / "diagrams").glob("*.json")):
        svg = path.with_suffix(".svg")
        if path.is_symlink() or svg.is_symlink() or not svg.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            continue
        if not any(_belongs(t, scope, feat, number) for t in graph._spec_ids(data, scope)):  # noqa: SLF001
            continue
        rows.append(
            {
                "svg": f"diagrams/{svg.name}",
                "json": f"diagrams/{path.name}",
                "embedded": svg.resolve() in shown,
            }
        )
    broken = [ref for ref, path in embeds(story, base) if path is None]
    return rows, broken


def _dismissed(fm: dict[str, Any]) -> bool:
    reason = str(fm.get("illustration_reason") or "").strip()
    return fm.get("illustration") == "none" and bool(reason)


def _chip(decision: str, dismissed: bool, covering: bool, stale: list[str]) -> str:
    if covering and stale:
        return CHECK
    if covering:
        return ILLUSTRATED
    if dismissed or decision == PROSE:
        return NONE
    if decision == DRAW:
        return NEEDS
    return CHECK


def assess(
    story: str,
    base: Path | None = None,
    scope: str | None = None,
    aliases: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Chip for one story. `base` supplies diagrams, the graph and other features' aliases."""
    parsed = frontmatter.parse(story)
    if parsed.error or not parsed.fm:
        raise ValueError(parsed.error or "story requires front matter")
    fm = parsed.fm
    feat = _bare(str(fm.get("id") or ""))
    chosen = scope or str(fm.get("scope") or "")
    if not ids.is_scope(chosen):
        raise ValueError("story requires a scope")
    number = ids.feat_number(feat)
    known = aliases if aliases is not None else _other_aliases(base, feat)
    signals = count_signals(story, known)
    decision = verdict(signals)
    live, withdrawn = _ids_in(story, chosen)
    if base is not None:
        disk_live, disk_gone = _scope_ids(base, chosen)
        # This story's own criteria win over a stale copy on disk.
        for key in list(disk_live):
            if _belongs(key, chosen, feat, number):
                disk_live.discard(key)
        for key in list(disk_gone):
            if _belongs(key, chosen, feat, number):
                disk_gone.discard(key)
        live |= disk_live
        withdrawn |= disk_gone
        live -= withdrawn
    rows = _citations(base, chosen, live, withdrawn)
    covering, stale = _covering(rows, chosen, feat, number)
    dismissed = _dismissed(fm)
    shown, broken = pictures(story, base, chosen, feat, number)
    return {
        "id": feat,
        "scope": chosen,
        "chip": _chip(decision, dismissed, covering, stale),
        "verdict": decision,
        "signals": signals.as_dict(),
        "dismissed": dismissed,
        "stale": stale,
        "pictures": shown,
        "broken": broken,
    }


def state(base: Path, feat: str, scope: str | None = None) -> dict[str, Any]:
    """Chip for the feature whose story is `base/02-drafts/FEAT-NNN.story.md`."""
    feature = _bare(feat)
    text = _story_path(Path(base), feature).read_text(encoding="utf-8")
    return assess(text, Path(base), scope)


def dismiss(base: Path, feat: str, reason: str) -> dict[str, Any]:
    """Record a prose decision in front matter. The body, and therefore the draft hash, stays."""
    text = " ".join(reason.split())
    if not text:
        raise ValueError("dismissal requires a reason")
    feature = _bare(feat)
    path = _story_path(Path(base), feature)
    original = path.read_text(encoding="utf-8")
    updated = frontmatter.update(original, {"illustration": "none", "illustration_reason": text})
    fsio.atomic_write(path, updated)
    return assess(updated, Path(base))


def render_text(result: dict[str, Any]) -> str:
    signals = result["signals"]
    lines = [
        f"{result['id']}  {result['chip']}",
        f"verdict: {result['verdict']}",
        f"actors: {signals['actors']}",
        f"branches: {signals['branches']}",
        f"state_changes: {signals['state_changes']}",
        f"handoffs: {signals['handoffs']}",
        f"data_moves: {signals['data_moves']}",
    ]
    if result["stale"]:
        lines.append("stale: " + ", ".join(result["stale"]))
    if result["dismissed"]:
        lines.append("dismissed: yes")
    loose = [p["svg"] for p in result.get("pictures", []) if not p["embedded"]]
    if loose:
        lines.append("not embedded: " + ", ".join(loose))
    if result.get("broken"):
        lines.append("image not found: " + ", ".join(result["broken"]))
    return "\n".join(lines) + "\n"
