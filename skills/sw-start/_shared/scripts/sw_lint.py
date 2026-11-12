#!/usr/bin/env python3
"""Check local contracts without editing them.

Exit 0: pass; 10/20/30: draft/review/publish blocked;
2: usage, workspace, I/O or unexpected checker failure. No network is used.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from urllib.parse import urlsplit

from kitlib import (  # noqa: E402
    borders,
    cite,
    frontmatter,
    fsio,
    graph,
    hashing,
    ids,
    illustration,
    invest,
    markdown,
    review,
    schema,
    tables,
    task_validation,
    workspace,
)

GATES = {"draft": 10, "review": 20, "publish": 30}
REVIEW = {f"L-{n:03}" for n in range(5, 16)} | {
    "L-017",
    "L-062",
    "L-064",
    "L-065",
    "L-066",
    "L-067",
}
PUBLISH = {"L-018", "L-037", "L-045", "L-046"}
SYNC = set()
RULE_IDS = {f"L-{n:03}" for n in (*range(1, 19), 24, *range(37, 56), *range(56, 68))}
RULE_HELP = {
    "L-001": "Front matter needs a mapping with non-empty id, type, status (scope in a program).",
    "L-002": "The id must use the grammar for its type, e.g. FEAT-003, BO-001, NFR-REF-001.",
    "L-003": "An ID or AC may only be defined once; a card and its draft are one item.",
    "L-004": "Each referenced ID must resolve to a doc, an AC, a reserved row or a tombstone.",
    "L-005": "A feature (or its card) must name at least one business objective in `bo:`.",
    "L-006": "A story needs at least two active acceptance criteria.",
    "L-007": "Each AC needs Given, When and Then in that order.",
    "L-008": "Each AC needs an observable detail: a number or a quoted literal.",
    "L-009": "Vague words (fast, robust, some) need an actor, threshold and condition.",
    "L-010": "An NFR needs a named metric, a numeric threshold and a condition.",
    "L-011": "Each business rule needs a worked `Example:` line.",
    "L-012": "List the four UI states or `None` with a reason.",
    "L-013": "Add at least one exclusion to Out of scope with a `reason:`.",
    "L-014": "Resolve `[NEEDS CLARIFICATION]` markers; more than three block.",
    "L-015": "Move implementation choices (SQL, endpoint, React) out of requirements.",
    "L-016": "The status must be valid for the document type.",
    "L-017": "AC IDs must match the feature, number 1..N, and keep withdrawn ones as tombstones.",
    "L-018": "Open questions must read `None` before publish or ready-for-dev.",
    "L-024": "Diagrams use full borders; a lone border on one side is not allowed.",
    "L-037": "A feature maps to exactly one Jira key and a published feature has a mapping.",
    "L-038": "A snapshot needs story sections, a Spec ID and a Draft hash in Identity.",
    "L-039": "A snapshot must not carry contract failures in its story sections.",
    "L-040": "A card needs card:true, home, links, a Summary and at most 150 words / 80 lines.",
    "L-041": "A snapshot differs from the published draft hash; record a CR first.",
    "L-042": "A published draft's body changed without a change request.",
    "L-043": "URLs must be https, scope must match, reference lists must hold spec IDs.",
    "L-044": "The Jira status must match the mapped repository status.",
    "L-045": "Record an accept, or fresh sign-offs with evidence and the hash for every role.",
    "L-046": "Use an action verb, a summary of at most 100 chars and all three identity labels.",
    "L-047": "A `.feature` export is stale; regenerate it from the draft.",
    "L-048": "A task traces to an acceptance criterion that is unresolved or withdrawn.",
    "L-049": "The knowledge graph is missing or stale; run graph.py build.",
    "L-050": "An epic reference does not resolve to an EPIC.",
    "L-051": "The epic's scopes list omits this project.",
    "L-052": "A `Touches` path is missing or unsafe.",
    "L-053": "A registry path must be relative, never absolute.",
    "L-054": "A named item needs a title and an aliases list (possibly empty).",
    "L-055": "The title is a placeholder; name the item.",
    "L-056": "A legacy ID in the text is not an alias of any artifact.",
    "L-057": "A citation must resolve to a real snapshot line with a matching hash.",
    "L-058": "A folder is unknown to the kit; list it in ignore_folders or remove it.",
    "L-059": "An open question must name the items it blocks in `affects`.",
    "L-060": "A decision records decided_by and evidence (a warning when sign-off is optional).",
    "L-061": "The decider must be a manifest approver (a warning when sign-off is optional).",
    "L-062": "A proposed amendment must be applied before review continues.",
    "L-063": "The INVEST split table needs pass/fail marks, not free text.",
    "L-064": "A feature needs an illustration and has no picture and no recorded dismissal.",
    "L-065": "A diagram cites an ID that is withdrawn or missing.",
    "L-066": "Each ASSET in `assets:` must be registered and cited in Context or UI/UX.",
    "L-067": "A mockup, link or image registered for this feature is missing from `assets:`.",
}
# Artifacts a reader looks up by name; each needs a title and an alias list (possibly empty).
NAMED_TYPES = {
    "feature",
    "idea",
    "epic",
    "q",
    "dec",
    "cr",
    "risk",
    "snapshot",
    "amendment",
    "candidates",
}
PLACEHOLDER_TITLES = {
    "reserved feature",
    "tbd",
    "tba",
    "todo",
    "untitled",
    "placeholder",
    "title",
    "n/a",
    "none",
}


def placeholder_title(title, identity=""):
    plain = str(title).strip().strip("()[]<>.").casefold()
    return not plain or plain in PLACEHOLDER_TITLES or plain == str(identity).casefold()


BANNED = (
    "fast",
    "quick",
    "slow",
    "efficient",
    "responsive",
    "scalable",
    "robust",
    "reliable",
    "flexible",
    "modern",
    "seamless",
    "user-friendly",
    "intuitive",
    "easy",
    "simple",
    "straightforward",
    "clean",
    "nice",
    "some",
    "many",
    "few",
    "several",
    "most",
    "various",
    "a lot",
    "minimal",
    "large",
    "small",
    "soon",
    "asap",
    "quickly",
    "real-time",
    "near real-time",
    "immediately",
    "periodically",
    "should",
    "may",
    "might",
    "could",
    "ideally",
    "preferably",
    "where possible",
    "if possible",
    "as appropriate",
    "as needed",
    "where applicable",
    "etc.",
    "and so on",
    "and/or",
    "tbd",
    "tbc",
    "appropriate",
    "adequate",
    "reasonable",
    "sufficient",
    "best practice",
    "industry standard",
    "state of the art",
    "compliant",
    "handle errors gracefully",
    "all",
    "always",
    "never",
    "every",
    "any",
    "ensure",
    "100%",
    "support",
    "handle",
    "manage",
    "process",
    "provide",
    "allow",
    "enable",
    "optimize",
    "improve",
    "enhance",
    "minimize",
    "maximize",
)
IMPL = (
    "sql",
    "endpoint",
    "microservice",
    "kafka",
    "redis",
    "react",
    "database table",
    "json",
    "http 500",
)
REQUIREMENTS = {
    "Goal",
    "Acceptance criteria",
    "Business rules",
    "Non-functional",
    "Edge cases and error behavior",
    "UI/UX",
}
JIRA_KEY = re.compile(r"[A-Z][A-Z0-9]+-\d+\Z")
VERBS = set(
    [
        "accept",
        "add",
        "adjust",
        "allow",
        "approve",
        "archive",
        "assign",
        "cancel",
        "capture",
        "change",
        "check",
        "close",
        "collect",
        "configure",
        "confirm",
        "create",
        "delete",
        "disable",
        "display",
        "download",
        "edit",
        "enable",
        "export",
        "filter",
        "find",
        "generate",
        "grant",
        "import",
        "list",
        "manage",
        "notify",
        "open",
        "pay",
        "record",
        "refund",
        "register",
        "reject",
        "remove",
        "request",
        "reset",
        "restore",
        "return",
        "revoke",
        "save",
        "search",
        "select",
        "send",
        "set",
        "show",
        "sign",
        "sort",
        "submit",
        "track",
        "update",
        "upload",
        "validate",
        "verify",
        "view",
    ]
)
EMPTY = {"", "—", "-", "None"}


def sequence(value):
    return value if isinstance(value, list) else []


def https(value):
    try:
        url = urlsplit(str(value))
        return (
            url.scheme == "https"
            and bool(url.netloc)
            and not url.username
            and not re.search(r"\s", str(value))
        )
    except ValueError:
        return False


def visible(body):
    """Blank fenced material without shifting source positions."""
    lines, fence = [], None
    for line in body.splitlines():
        m = re.match(r"^\s*(\x60{3,}|~{3,})", line)
        if m:
            if fence is None:
                fence = m.group(1)
            elif m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence):
                fence = None
            lines.append("")
        else:
            lines.append("" if fence else line)
    return "\n".join(lines)


@dataclass
class Doc:
    path: str
    raw: str
    parsed: frontmatter.Parsed

    @classmethod
    def read(cls, path, base):
        return cls.from_text(str(path.relative_to(base)), path.read_text(encoding="utf-8"))

    @classmethod
    def from_text(cls, path, raw):
        return cls(path, raw, frontmatter.parse(raw))

    @property
    def fm(self):
        return self.parsed.fm or {}

    @property
    def spec_id(self):
        return str(self.fm.get("id", ""))

    @property
    def snapshot(self):
        return self.fm.get("type") == "snapshot" and self.fm.get("source_kind") == "jira-issue"

    @property
    def card(self):
        return self.fm.get("card") is True or self.path.endswith(".card.md")

    @property
    def story(self):
        return self.snapshot or (self.fm.get("type") == "feature" and not self.card)

    @property
    def body(self):
        return visible(self.parsed.body)

    @property
    def sec(self):
        return markdown.sections(self.body, first_line=self.parsed.body_line)

    @property
    def ac(self):
        return markdown.ac_blocks(self.sec.get("Acceptance criteria"))

    def text(self, section):
        sec = self.sec.get(section)
        return sec.text if sec else ""

    def line(self, section):
        sec = self.sec.get(section)
        return sec.line if sec else self.parsed.body_line


@dataclass(frozen=True)
class Finding:
    rule: str
    gate: str
    sev: str
    path: str
    line: int
    msg: str
    subject: str = ""
    waiver: str = ""


class Context:
    def __init__(
        self,
        base,
        scope="REF",
        gate="review",
        program=False,
        docs=(),
        manifest=None,
        definitions=None,
        registry=None,
        built=None,
    ):
        self.base, self.scope, self.gate, self.program = Path(base), scope, gate, program
        self.docs = list(docs)
        self.manifest = manifest or {}
        self.definitions = definitions or set()
        self.registry = registry or tables.Table(list(schema.REGISTRY_COLUMNS))
        self.waivers = []
        self.built = built
        self._sources = None

    @property
    def sources(self):
        if self._sources is None:
            self._sources = cite.Sources(self.base)
        return self._sources

    def feature(self, doc):
        if not doc.snapshot:
            return doc.spec_id
        for key in ("spec_id", "feature_id"):
            ref = ids.parse_ref(str(doc.fm.get(key, "")))
            if ref and ref.id.startswith("FEAT-"):
                return ref.id
        match = re.search(r"Spec ID:\s*(?:[A-Z]{2,5}:)?(FEAT-\d{3})\b", doc.text("Identity"))
        if match:
            return match.group(1)
        for row in self.registry.rows:
            if self.registry.get(row[0], "Last snapshot") == doc.path:
                ref = ids.parse_ref(row[0])
                return ref.id if ref else ""
        return ""

    def rowkey(self, doc):
        feat = self.feature(doc)
        for key in (ids.qualify(self.scope, feat), feat):
            if self.registry.find(key):
                return key
        return ids.qualify(self.scope, feat)

    def cell(self, doc, column):
        return self.registry.get(self.rowkey(doc), column) or ""

    def changed_with_record(self, doc):
        target = self.feature(doc)
        return any(
            d.fm.get("type") == "cr"
            and d.fm.get("status") != "withdrawn"
            and any(
                r.id == target and (r.scope or self.scope) == self.scope
                for r in ids.find_refs(d.raw)
            )
            for d in self.docs
        )


def rule_gate(rule):
    return "publish" if rule in PUBLISH else "review" if rule in REVIEW else "draft"


def strict_or_named(who: dict, strict: bool) -> bool:
    """The owner deciding for themselves needs no approver unless sign-off is required."""
    owner = str(who.get("role", "")).casefold() == "owner"
    return strict or not (owner and str(who.get("name", "")).casefold() == "self")


def lint_document(doc, ctx):
    """Emit decidable checks; wording quality remains a human responsibility."""
    findings = []

    def emit(rule, message, line=1, subject="", sev="error"):
        gate = rule_gate(rule)
        if list(GATES).index(gate) <= list(GATES).index(ctx.gate):
            if rule in {"L-009", "L-015", "L-041", "L-044", "L-064", "L-065", "L-067"}:
                sev = "warn"
            if rule == "L-012" and ctx.gate == "review":
                sev = "warn"
            # Imported snapshots are immutable evidence: they are reported but never block a gate.
            if doc.path.startswith("00-inbox/") and sev == "error":
                sev = "warn"
            findings.append(
                Finding(
                    rule,
                    gate,
                    sev,
                    doc.path,
                    line,
                    message,
                    subject or ctx.feature(doc) or doc.spec_id,
                )
            )

    for line, message in borders.find_one_sided(doc.raw):
        emit("L-024", message, line)
    if not doc.path.endswith(".md"):
        return findings
    fm = doc.fm
    missing = [
        k
        for k in ("id", "type", "status", *(("scope",) if ctx.program else ()))
        if not isinstance(fm.get(k), str) or not fm[k].strip()
    ]
    if doc.parsed.error or doc.parsed.fm is None or missing:
        emit(
            "L-001",
            doc.parsed.error or f"front matter requires {', '.join(missing) or 'a mapping'}",
        )
        return findings
    if not ids.matches_type(str(fm["type"]), doc.spec_id):
        emit("L-002", "use the ID grammar for this document type")
    if fm.get("status") not in schema.STATUSES.get(fm["type"], []):
        emit("L-016", "status is not valid for this type")
    if fm.get("scope", ctx.scope) != ctx.scope:
        emit("L-043", "front matter scope differs from the selected project")
    if fm["type"] == "q" and fm.get("status") != "withdrawn":
        targets = [r for f in ("affects", "affected") for r in ids.find_refs(str(fm.get(f, "")))]
        if not targets:
            emit("L-059", "a question names the items it blocks in `affects`")
    if fm["type"] == "dec" and not (
        fm.get("subtype") == "lifecycle"
        or fm.get("origin") == "local-transition"
        or fm.get("waives")
    ):
        # Strict governance blocks on these; with optional sign-off they are advice, because a solo
        # owner decides without a configured approver or a link.
        strict = workspace.governance_of(ctx.manifest)["signoff"] == "required"
        sev = "error" if strict else "warn"
        who = fm.get("decided_by")
        who = who if isinstance(who, dict) else {}
        if not str(who.get("role", "")).strip() or not str(who.get("name", "")).strip():
            emit("L-060", "a decision records decided_by with a role and a name", sev=sev)
        elif (
            strict_or_named(who, strict)
            and (approvers := sequence(ctx.manifest.get("approvers")))
            and not any(
                str(a.get("role", "")).casefold() == str(who["role"]).casefold()
                and str(a.get("name", "")).casefold() == str(who["name"]).casefold()
                for a in approvers
                if isinstance(a, dict)
            )
        ):
            emit(
                "L-061",
                f"{who['name']} ({who['role']}) is not in the manifest approvers",
                sev=sev,
            )
        if (
            fm.get("evidence_kind") not in schema.EVIDENCE_KINDS
            or not str(fm.get("evidence_ref", "")).strip()
        ):
            emit("L-060", "a decision records evidence_kind and evidence_ref", sev=sev)
        elif strict and fm.get("evidence_kind") == schema.SESSION_EVIDENCE:
            emit("L-060", "session evidence is not accepted when sign-off is required")
    if fm["type"] == "idea":
        for problem in invest.problems(doc.body):
            emit("L-063", problem)
    if fm["type"] == "feature" and not doc.card:
        pending = sorted(
            d.spec_id
            for d in ctx.docs
            if d.fm.get("type") == "amendment"
            and d.fm.get("status") == "proposed"
            and doc.spec_id in {r.id for r in ids.find_refs(str(d.fm.get("affects", "")))}
        )
        if pending:
            emit("L-062", f"pending amendment(s) {', '.join(pending)}: apply or reject first")
    if not doc.snapshot and fm["type"] not in {"snapshot", "src"}:
        for problem in cite.problems(ctx.sources, doc.raw):
            emit("L-057", problem.message, problem.line, sev=problem.severity)
    if fm["type"] in NAMED_TYPES and not doc.card:
        # Snapshots are immutable, so an old one without a name is a warning, not a blocker.
        severity = "warn" if fm["type"] == "snapshot" else "error"
        absent = [k for k in ("title", "aliases") if k not in fm or (k == "title" and not fm[k])]
        if absent or not isinstance(fm.get("aliases"), list):
            emit(
                "L-054",
                f"front matter needs {' and '.join(absent or ['aliases as a list'])}",
                sev=severity,
            )
        elif placeholder_title(fm["title"], doc.spec_id):
            emit("L-055", f"title '{fm['title']}' is a placeholder; name the item", sev=severity)
    role = "card" if doc.card else "snapshot" if doc.snapshot else "definition"
    if role != "snapshot" and fm["type"] not in {"snapshot", "src"}:
        peers = [
            d
            for d in ctx.docs
            if d.spec_id == doc.spec_id
            and ("card" if d.card else "snapshot" if d.snapshot else "definition") == role
        ]
        if len(peers) > 1:
            emit("L-003", "ID has multiple definitions in this representation")
    for ref in ids.find_refs(doc.raw):
        if (not ref.scope or ref.scope == ctx.scope) and (
            ref.id == doc.spec_id or ref.id in doc.ac or ref.id in ids.tombstones(doc.body)
        ):
            continue
        if ids.qualify(ref.scope or ctx.scope, ref.id) not in ctx.definitions:
            emit(
                "L-004",
                f"unresolved reference {ref.qualified}",
                next(
                    (
                        n
                        for n, line in enumerate(doc.raw.splitlines(), 1)
                        if ref in ids.find_refs(line)
                    ),
                    1,
                ),
                subject=ref.id,
            )
    for key, value in fm.items():
        values = value if isinstance(value, list) else [value]
        if key in {"jira_key", "jira_parent"}:
            for val in values:
                if str(val) not in EMPTY and val is not None and not JIRA_KEY.fullmatch(str(val)):
                    emit("L-043", f"invalid Jira key in {key}")
        if key in {"links", "source", "evidence", "evidence_url"}:
            for val in values:
                url_required = key != "source" or str(val).startswith(("http:", "https:"))
                if url_required and not https(val):
                    emit("L-043", f"{key} requires an https URL")
        if key in {"bo", "br", "nfr", "sources", "applies_to", "affected_ids"} and (
            not isinstance(value, list) or any(ids.parse_ref(str(v)) is None for v in values)
        ):
            emit("L-043", f"{key} must be a list of spec references")
    for number, line in enumerate(doc.body.splitlines(), doc.parsed.body_line):
        if re.search(r"\bhttp://[^\s)>]+", line):
            emit("L-043", "replace insecure URL with https", number)
    if doc.card:
        summary = doc.text("Summary")
        checks = [
            ("card:true", fm.get("card") is True),
            ("home", bool(fm.get("home"))),
            ("links", bool(sequence(fm.get("links")))),
            ("<=80 file lines", len(doc.raw.splitlines()) <= 80),
            ("Summary section", bool(summary)),
            ("Summary <=150 words", bool(summary) and len(summary.split()) <= 150),
        ]
        failed = [name for name, ok in checks if not ok]
        if failed:
            emit(
                "L-040",
                "card fails: " + ", ".join(failed),
            )
    if fm["type"] == "feature":
        bo_refs = [
            r
            for v in sequence(fm.get("bo"))
            for r in ids.find_refs(str(v))
            if r.id.startswith("BO-")
        ]
        if not bo_refs:
            emit("L-005", "feature needs at least one BO reference")
    if doc.story:
        if len(doc.ac) < 2:
            emit(
                "L-006",
                "provide at least two active acceptance criteria",
                doc.line("Acceptance criteria"),
            )
        acsec = doc.sec.get("Acceptance criteria")
        headings = markdown.iter_sections(doc.body, level=3, first_line=doc.parsed.body_line)
        acid_list = [s.name.split()[0] for s in headings if s.name.startswith("AC-")]
        if len(acid_list) != len(set(acid_list)):
            emit("L-003", "acceptance criterion ID is repeated", doc.line("Acceptance criteria"))
        feat = ctx.feature(doc)
        numbers = []
        for acid in [*doc.ac, *markdown.ac_tombstones(acsec)]:
            parsed = ids.parse_ac(acid)
            if parsed and feat == f"FEAT-{parsed[0]:03}" and parsed[1] > 0:
                numbers.append(parsed[1])
            else:
                emit(
                    "L-017",
                    f"{acid} must match {feat} and use a positive ordinal",
                    doc.line("Acceptance criteria"),
                    acid,
                )
        if numbers and (
            len(numbers) != len(set(numbers))
            or min(numbers) != 1
            or len(set(numbers)) != max(numbers)
        ):
            emit(
                "L-017",
                "keep withdrawn ordinals as tombstones; do not reuse them",
                doc.line("Acceptance criteria"),
            )
        if acsec:
            for number, line in acsec.lines:
                if line.startswith("### ") and not re.match(r"### AC-\d{3}-\d+\b", line):
                    emit("L-017", "acceptance heading needs a numbered AC ID", number)
        for acid, ac in doc.ac.items():
            positions = [
                re.search(rf"\b{word}\b", ac.text, re.I) for word in ("Given", "When", "Then")
            ]
            if any(p is None for p in positions) or [p.start() for p in positions if p] != sorted(
                p.start() for p in positions if p
            ):
                emit("L-007", f"{acid}: put Given, When, Then in order", ac.line, acid)
            if not re.search(
                r'\d|"[^"\n]+"|“[^”\n]+”|(?<!\w)\x27[^\x27\n]+\x27|\x60[^\x60\n]+\x60', ac.text
            ):
                emit("L-008", f"{acid}: add a number or observable literal", ac.line, acid)
        ui = doc.text("UI/UX")
        if not re.search(r"\bNone\s*[—–-]\s*\S", ui, re.I) and not all(
            re.search(rf"\b{s}\b", ui, re.I) for s in ("default", "empty", "loading", "error")
        ):
            emit("L-012", "list four UI states or None with a reason", doc.line("UI/UX"))
        registry = task_validation.asset_rows(ctx.base)
        listed = [r.id for v in sequence(fm.get("assets")) for r in ids.find_refs(str(v))]
        shown = doc.text("Context") + "\n" + doc.text("UI/UX")
        for asset in dict.fromkeys(listed):
            if asset not in registry:
                emit("L-066", f"{asset} is not in the asset registry", doc.line("UI/UX"), asset)
            elif asset not in shown:
                emit("L-066", f"cite {asset} in UI/UX so readers see it", doc.line("UI/UX"), asset)
        for asset, (kind, refs) in registry.items():
            named = {r.id for r in ids.find_refs(refs)}
            if feat in named and kind in schema.VISUAL_ASSET_KINDS and asset not in listed:
                emit(
                    "L-067", f"add {asset} ({kind}) to assets: and UI/UX", doc.line("UI/UX"), asset
                )
        items = [
            line for line in doc.text("Out of scope").splitlines() if re.match(r"\s*[-*] ", line)
        ]
        if not items or any(not re.search(r"reason:\s*\S", line, re.I) for line in items):
            emit("L-013", "add at least one exclusion with reason:", doc.line("Out of scope"))
        if (
            fm["status"] in {"ready-to-publish", "published", "ready-for-dev"}
            and doc.text("Open questions").strip() != "None"
        ):
            emit("L-018", "resolve Open questions to None", doc.line("Open questions"))
    markers = doc.body.count("[NEEDS CLARIFICATION")
    if markers > 3 or (markers and ctx.gate == "publish"):
        if markers > 3 and ctx.gate == "draft":
            findings.append(
                Finding(
                    "L-014",
                    "draft",
                    "error",
                    doc.path,
                    doc.parsed.body_line,
                    f"resolve clarification markers ({markers} remain)",
                    ctx.feature(doc) or doc.spec_id,
                )
            )
        else:
            emit("L-014", f"resolve clarification markers ({markers} remain)", doc.parsed.body_line)
    requirement_lines = []
    for section in doc.sec.values():
        if section.name in REQUIREMENTS or fm["type"] in {"bo", "br", "fr", "nfr"}:
            requirement_lines.extend((section.name, n, text) for n, text in section.lines)
    if fm["type"] in {"bo", "br", "fr", "nfr"} and not doc.sec:
        requirement_lines = [
            ("Requirement", n, text)
            for n, text in enumerate(doc.body.splitlines(), doc.parsed.body_line)
        ]
    for section, number, text in requirement_lines:
        if text.startswith(("#", ">")):
            continue
        prose = re.sub(
            r'"[^"\n]*"|“[^”\n]*”|(?<!\w)\x27[^\x27\n]*\x27|\x60[^\x60\n]*\x60', "", text
        )
        prose = re.sub(r"\b(?:Must|Should|Could|Won't) have\b", "", prose, flags=re.I)
        for word in BANNED:
            if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", prose, re.I):
                emit(
                    "L-009",
                    f"replace vague '{word}' with actor, threshold and condition",
                    number,
                )
        if re.match(
            r"^\s*(?:[-*]\s+)?(?:Given |When |Then )?(?:it|they|this|that)\s+"
            r"(?:shall|must|will|is|are|can)\b",
            prose,
            re.I,
        ):
            emit("L-009", "name the subject instead of an ambiguous pronoun", number)
        if re.search(r"\bsecure\b", prose, re.I) and not re.search(
            r"\b(tls|encrypt\w*|role|mfa|owasp)\b", prose, re.I
        ):
            emit("L-009", "qualify secure with a control and measurable scope", number)
        if section in {"Goal", "Acceptance criteria", "Business rules"} or fm["type"] in {
            "bo",
            "br",
        }:
            for word in IMPL:
                if re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", prose, re.I):
                    emit("L-015", f"move implementation choice '{word}' to design", number)
    nfr_text = doc.text("Non-functional") if doc.story else doc.body if fm["type"] == "nfr" else ""
    nfr_items = [s for s in re.split(r"\n(?=\s*[-*] )", nfr_text) if s.strip()]
    if doc.story and not nfr_items:
        emit(
            "L-010", "supply metric, threshold and operating condition", doc.line("Non-functional")
        )
    for item in nfr_items:
        metric = re.search(
            r"\b(response|latency|time|uptime|availability|throughput|contrast|wcag|retain|retention|rto|rpo|error|rate|records|requests|percentile|p\d+)\b",
            item,
            re.I,
        )
        threshold = re.search(r"\d", re.sub(r"NFR-[A-Z]{2,5}-\d{3}", "", item))
        condition = re.search(
            r"\b(under|at|during|when|per|over|within|for|measured|verified)\b", item, re.I
        )
        if not (metric and threshold and condition):
            emit(
                "L-010",
                "NFR needs a named metric, numeric threshold and condition",
                doc.line("Non-functional"),
            )
    br_text = doc.text("Business rules") if doc.story else doc.body if fm["type"] == "br" else ""
    for item in re.split(r"\n(?=\s*[-*] BR-)", br_text):
        if item.strip() and not re.search(r"\bExample:\s*\S", item, re.I):
            emit(
                "L-011", "add a worked Example: for each business rule", doc.line("Business rules")
            )
    if doc.snapshot:
        got = [s.name for s in markdown.iter_sections(doc.body) if s.name in schema.STORY_SECTIONS]
        identity = doc.text("Identity")
        if (
            got != schema.STORY_SECTIONS
            or not re.search(r"Spec ID:\s*(?:[A-Z]{2,5}:)?FEAT-\d{3}\b", identity)
            or not re.search(r"Draft hash:\s*sha256:[0-9a-f]{64}\b", identity)
        ):
            emit(
                "L-038", "snapshot needs ordered story sections and Identity spec ID and draft hash"
            )
        failures = sorted(
            {
                f.rule
                for f in findings
                if f.rule in {f"L-{n:03}" for n in range(6, 16)} and f.sev == "error"
            }
        )
        if failures:
            emit("L-039", "snapshot contract checks failed: " + ", ".join(failures))
    published = ctx.cell(doc, "Last published draft hash")
    has_cr = ctx.changed_with_record(doc)
    if doc.story and published not in EMPTY and not has_cr:
        if doc.snapshot:
            latest = ctx.cell(doc, "Last snapshot")
            candidates = sorted(
                d.path for d in ctx.docs if d.snapshot and ctx.feature(d) == ctx.feature(doc)
            )
            latest = latest if latest not in EMPTY else max(candidates, default="")
            if doc.path == latest and hashing.draft_hash(doc.raw) != published:
                emit("L-041", "snapshot description differs from the published hash; record a CR")
        elif hashing.draft_hash(doc.raw) != published:
            emit("L-042", "published draft body changed without a CR")
    if doc.snapshot:
        status_map = ctx.manifest.get("status_map") or schema.DEFAULT_STATUS_MAP
        expected = status_map.get(fm.get("repo_status", ""))
        if not expected:
            draft = next(
                (
                    d
                    for d in ctx.docs
                    if not d.snapshot and d.story and d.spec_id == ctx.feature(doc)
                ),
                None,
            )
            expected = status_map.get(draft.fm.get("status")) if draft else None
        if fm.get("jira_status") and expected and fm["jira_status"] != expected:
            emit("L-044", f"Jira status differs from mapped repository status ({expected})")
    if fm["type"] == "feature" and not doc.card:
        if fm["status"] in {"ready-to-publish", "published", "ready-for-dev"}:
            valid_roles = set()
            digest = hashing.draft_hash(doc.raw)
            for entry in sequence(fm.get("signoffs")):
                if isinstance(entry, dict):
                    role, name, evidence, signed_hash = (
                        entry.get(k) for k in ("role", "name", "evidence", "draft_hash")
                    )
                else:
                    parts = [s.strip() for s in str(entry).split("|")]
                    role, name, evidence, signed_hash = (
                        (parts[0], parts[1], parts[3], parts[4]) if len(parts) == 5 else (None,) * 4
                    )
                if role and name and https(evidence) and signed_hash == digest:
                    valid_roles.add(role)
            required = {
                a.get("role")
                for a in sequence(ctx.manifest.get("approvers"))
                if isinstance(a, dict) and a.get("role")
            } or {"PO"}
            short = hashing.short(digest)
            accepted = workspace.governance_of(ctx.manifest)["signoff"] == "optional" and any(
                (m := review.ACCEPT_LINE.match(str(e))) and m.group(1) == short
                for e in sequence(fm.get("signoffs"))
            )
            if not accepted and not required <= valid_roles:
                emit(
                    "L-045",
                    "record fresh sign-offs with evidence and draft hash for: "
                    + ", ".join(sorted(required - valid_roles)),
                )
        summary = str(fm.get("jira_summary", ""))
        first = summary.split()[0].lower() if summary.split() else ""
        need = {"specwright", f"feat:{doc.spec_id}", f"proj:{ctx.scope}"}
        if (
            len(summary) > 100
            or first not in VERBS
            or not need <= set(str(v) for v in sequence(fm.get("jira_labels")))
        ):
            emit(
                "L-046",
                "use a recognized action verb, summary <=100 chars and all three identity labels",
            )
    if fm.get("type") == "feature" and doc.story and not doc.card:
        try:
            picture = illustration.assess(doc.raw, ctx.base, ctx.scope)
        except ValueError:
            picture = None
        if picture and picture["chip"] == illustration.NEEDS:
            emit(
                "L-064",
                "feature needs an illustration and has no recorded dismissal",
                sev="warn",
            )
        if picture and picture["stale"]:
            emit(
                "L-065",
                "a diagram cites a withdrawn or missing ID: " + ", ".join(picture["stale"]),
                sev="warn",
            )
    return findings


def definitions_for(docs, scope):
    defined = set()
    for doc in docs:
        if doc.parsed.error:
            continue
        if doc.spec_id:
            defined.add(ids.qualify(scope, doc.spec_id))
        if not doc.snapshot:
            defined.update(
                ids.qualify(scope, acid) for acid in [*doc.ac, *ids.tombstones(doc.body)]
            )
    return defined


def registry_definitions(registry, scope):
    """Reserved, non-withdrawn registry rows count as definitions before a draft exists."""
    defined = set()
    for row in registry.rows:
        ref = ids.parse_ref(row[0])
        if ref and registry.value(row[0], "State") not in ("withdrawn", "superseded"):
            defined.add(ids.qualify(scope, ref.id))
    return defined


def discover(base, ignore=()):
    """Exclude originals, derived reports and installed code from document checks."""
    if base.is_symlink():
        raise workspace.WorkspaceError("scope directory must not be a symbolic link")
    skip = {
        "_meta",
        "raw",
        ".git",
        ".agents",
        ".claude",
        "skills",
        "projects",
        "console",
        "node_modules",
        "03-plan",
        *(str(i).strip("/") for i in ignore),
    }
    docs = []
    for path in sorted(base.rglob("*")):
        parts = path.relative_to(base).parts
        if any(p in skip for p in parts):
            continue
        if path.name in {"AGENTS.md", "CLAUDE.md", "GEMINI.md", "README.md"}:
            continue
        if path.is_symlink():
            raise workspace.WorkspaceError(f"refusing symbolic link {path}")
        if path.is_file() and path.suffix in {".md", ".html", ".css", ".svg"}:
            try:
                docs.append(Doc.read(path, base))
            except UnicodeError:
                docs.append(Doc.from_text(str(path.relative_to(base)), "---\ninvalid: [\n---\n"))
    return docs


def registry_findings(ctx):
    out = []
    by_feature, by_key = {}, {}
    defined = {d.spec_id for d in ctx.docs if d.fm.get("type") == "feature"}
    for row in ctx.registry.rows:
        ref = ids.parse_ref(row[0])
        if not ref or (ref.scope and ref.scope != ctx.scope) or not ref.id.startswith("FEAT-"):
            continue
        state = ctx.registry.value(row[0], "State")
        reserved = ref.id not in defined and state not in ("withdrawn", "superseded")
        if reserved and placeholder_title(ctx.registry.value(row[0], "Title"), ref.id):
            out.append(
                Finding(
                    "L-055",
                    "draft",
                    "error",
                    "_meta/id-registry.md",
                    1,
                    "reserved feature has no real title; record one with the reservation",
                    ref.id,
                )
            )
        key = ctx.registry.get(row[0], "Jira key") or ""
        if key in EMPTY:
            continue
        if not JIRA_KEY.fullmatch(key):
            out.append(
                Finding(
                    "L-043",
                    "draft",
                    "error",
                    "_meta/id-registry.md",
                    1,
                    f"invalid Jira key {key}",
                    ref.id,
                )
            )
        by_feature.setdefault(ref.id, set()).add(key)
        by_key.setdefault(key, set()).add(ref.id)
    if ctx.gate == "publish":
        for feat, keys in sorted(by_feature.items()):
            if len(keys) > 1:
                out.append(
                    Finding(
                        "L-037",
                        "publish",
                        "error",
                        "_meta/id-registry.md",
                        1,
                        "feature maps to several Jira keys",
                        feat,
                    )
                )
        for key, feats in sorted(by_key.items()):
            if len(feats) > 1:
                for feat in sorted(feats):
                    out.append(
                        Finding(
                            "L-037",
                            "publish",
                            "error",
                            "_meta/id-registry.md",
                            1,
                            f"Jira key {key} maps to several features",
                            feat,
                        )
                    )
        for doc in ctx.docs:
            if (
                doc.fm.get("type") == "feature"
                and doc.fm.get("status") in {"published", "ready-for-dev"}
                and doc.spec_id not in by_feature
            ):
                out.append(
                    Finding(
                        "L-037",
                        "publish",
                        "error",
                        doc.path,
                        1,
                        "published feature has no Jira registry mapping",
                        doc.spec_id,
                    )
                )
    return out


def load_waivers(ctx):
    """Only decision records with explicit targets and evidence can excuse findings."""
    for doc in ctx.docs:
        if (
            not re.fullmatch(r"records/DEC-\d{3}(--[^/]*)?\.md", doc.path)
            or doc.fm.get("type") != "dec"
            or doc.fm.get("status") != "accepted"
            or doc.parsed.error
        ):
            continue
        evidence = doc.fm.get("evidence_url", doc.fm.get("evidence", ""))
        if not https(evidence):
            evidence = next(
                (
                    u.rstrip(".,)")
                    for u in re.findall(r"https://[^\s<>]+", doc.body)
                    if https(u.rstrip(".,)"))
                ),
                "",
            )
        if not evidence:
            continue
        for rule in sequence(doc.fm.get("waives")):
            if rule not in RULE_IDS:
                continue
            for target in sequence(doc.fm.get("applies_to")):
                ref = ids.parse_ref(str(target))
                if ref and (ref.scope or ctx.scope) == ctx.scope:
                    ctx.waivers.append((rule, ref.id, doc.path, str(evidence)))
    ctx.waivers.sort()


def apply_waivers(findings, ctx):
    return [
        replace(
            f,
            waiver=next(
                (
                    f"{path} ({url})"
                    for rule, target, path, url in ctx.waivers
                    if f.rule == rule and f.subject == target
                ),
                "",
            ),
        )
        for f in findings
    ]


def graph_findings(ctx):
    """Links across epics, tasks, exports and the graph; never trusts the graph blindly."""
    root = workspace.find_root(ctx.base)
    out = []

    def add(rule, sev, path, line, msg, subject):
        gate = rule_gate(rule)
        if list(GATES).index(gate) <= list(GATES).index(ctx.gate):
            out.append(Finding(rule, gate, sev, path, line, msg, subject))

    for name in workspace.stray_folders(ctx.base, ctx.manifest.get("ignore_folders") or []):
        add(
            "L-058",
            "warn",
            f"{name}/",
            1,
            "folder is unknown to the kit; nothing in it is read",
            name,
        )
    for row in ctx.registry.rows:
        cell = row[ctx.registry.col("Last snapshot")]
        if cell.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", cell):
            add("L-053", "warn", "_meta/id-registry.md", 1, "registry path is absolute", row[0])

    if ctx.built is not None:
        built = ctx.built
    else:
        if root is None:
            add(
                "L-049",
                "warn",
                "_meta/graph",
                1,
                "no workspace manifest; the graph cannot be checked",
                ctx.scope,
            )
            return out
        known = workspace.list_scopes(root)
        try:
            built = graph.build_graph(root, known, known)
        except (OSError, ValueError):
            add(
                "L-049",
                "warn",
                "_meta/graph",
                1,
                "knowledge graph could not be built; the workspace has unreadable content",
                ctx.scope,
            )
            return out

    prefix = f"{ctx.scope}:"
    epic_scopes = {k: n.extra.get("scopes", []) for k, n in built.nodes.items() if n.kind == "epic"}
    for e in built.edges:
        if not e.src.startswith(prefix) or e.cls == "mentioned":
            continue
        if e.rel == "member_of" and e.cls == "declared":
            if e.res == "unresolved" or (
                e.dst in built.nodes and built.nodes[e.dst].kind != "epic"
            ):
                add(
                    "L-050",
                    "error",
                    e.file,
                    e.line,
                    "epic reference does not resolve to an EPIC",
                    e.src,
                )
            elif e.dst in epic_scopes and ctx.scope not in epic_scopes[e.dst]:
                add(
                    "L-051",
                    "error",
                    e.file,
                    e.line,
                    "the epic's scopes list omits this project",
                    e.src,
                )
        if e.rel == "implements" and e.res in ("unresolved", "withdrawn"):
            add(
                "L-048", "error", e.file, e.line, f"task traces to {e.dst}, which is {e.res}", e.src
            )
        if e.rel == "touches" and e.res in ("missing", "unsafe-path", "no-code-root"):
            add("L-052", "warn", e.file, e.line, f"Touches path is {e.res}: {e.dst}", e.src)

    for key, node in built.nodes.items():
        if not key.startswith(prefix):
            continue
        if node.kind == "feature-file":
            owner = built.nodes.get(node.owner)
            try:
                draft = (ctx.base / owner.path).read_text(encoding="utf-8") if owner else ""
            except OSError:
                draft = ""
            if owner and draft and node.extra.get("source_hash") != hashing.draft_hash(draft):
                add(
                    "L-047",
                    "warn",
                    node.path,
                    1,
                    ".feature export is stale; regenerate it",
                    node.owner,
                )

    if root is not None:
        out.extend(_graph_state(ctx, root, add))
    return out


def _graph_state(ctx, root, add):
    if root is None:
        return []
    outdir = graph.graph_dir(root, ctx.scope)
    manifest = outdir / "manifest.json"
    if not manifest.is_file():
        add(
            "L-049",
            "warn",
            "_meta/graph",
            1,
            "knowledge graph is missing; run graph.py build",
            ctx.scope,
        )
        return []
    try:
        recorded = json.loads(manifest.read_text(encoding="utf-8")).get("inputs_digest")
        current = graph.digest(root, graph.input_files(root, [ctx.scope]))
    except (OSError, ValueError):
        recorded, current = None, "x"
    if recorded != current:
        add(
            "L-049",
            "warn",
            "_meta/graph",
            1,
            "knowledge graph is stale; run graph.py build",
            ctx.scope,
        )
    return []


def legacy_findings(ctx):
    """A legacy ID written in a body must be an alias of some artifact, or the item is unmapped."""
    patterns = [
        str(s.get("legacy_id_pattern", "")).strip().removeprefix("^").removesuffix("$")
        for s in sequence(ctx.manifest.get("sources"))
        if isinstance(s, dict) and s.get("legacy_id_pattern")
    ]
    if not patterns:
        return []
    try:
        regex = re.compile(r"(?<![\w-])(?:" + "|".join(patterns) + r")(?![\w-])")
    except re.error:
        return []
    known = {
        str(a).casefold()
        for doc in ctx.docs
        for a in (doc.fm.get("aliases") if isinstance(doc.fm.get("aliases"), list) else [])
    }
    for row in ctx.registry.rows:
        known |= {a.casefold() for a in ctx.registry.value(row[0], "Aliases").split("|") if a}
    out = []
    for doc in ctx.docs:
        if doc.snapshot or doc.fm.get("type") in {"snapshot", "src", "candidates"}:
            continue
        for number, line in enumerate(doc.body.splitlines(), doc.parsed.body_line):
            for match in regex.finditer(line):
                if match.group(0).casefold() not in known:
                    out.append(
                        Finding(
                            "L-056",
                            "draft",
                            "error",
                            doc.path,
                            number,
                            f"legacy ID {match.group(0)} is not an alias of any artifact",
                            doc.spec_id,
                        )
                    )
    return out


def collect(ctx):
    findings = [f for doc in ctx.docs for f in lint_document(doc, ctx)]
    findings.extend(legacy_findings(ctx))
    findings.extend(registry_findings(ctx))
    findings.extend(graph_findings(ctx))
    # A card and its draft describe the same identity, but independent drafts cannot own an AC.
    owners = {}
    for doc in ctx.docs:
        if not doc.snapshot and not doc.card:
            for acid in [*doc.ac, *ids.tombstones(doc.body)]:
                owners.setdefault(acid, set()).add(doc.path)
    for acid, paths in owners.items():
        if len(paths) > 1:
            for path in sorted(paths):
                findings.append(
                    Finding("L-003", "draft", "error", path, 1, f"{acid} has multiple owners", acid)
                )
    return sorted(
        apply_waivers(findings, ctx),
        key=lambda f: (f.path, f.line, f.rule, f.subject, f.msg, f.waiver),
    )


def report_text(ctx, findings):
    table = tables.Table(["Rule", "Severity", "Location", "Subject", "Message", "Waiver"])
    table.rows = [
        [f.rule, f.sev, f"{f.path}:{f.line}", f.subject, f.msg, f.waiver or "—"] for f in findings
    ]
    errors = sum(f.sev == "error" and not f.waiver for f in findings)
    header = (
        f"# Lint report\n\nScope: {ctx.scope} · Gate: {ctx.gate}\n\n{errors} blocking error(s).\n\n"
    )
    waivers = tables.Table(["Rule", "Applies to", "Decision", "Evidence"])
    waivers.rows = [list(w) for w in ctx.waivers]
    return header + table.render() + "\n## Recognized waivers\n\n" + waivers.render()


def run(root, gate="review", scope=None):
    start = Path(root).resolve()
    if not start.is_dir():
        raise workspace.WorkspaceError("root must be an existing directory")
    workspace_root = workspace.find_root(start)
    if workspace_root is None:
        raise workspace.WorkspaceError(
            "no workspace manifest; run the sw-start workspace setup first"
        )
    selected = workspace.resolve(workspace_root, arg=scope, cwd=start, write=True)
    base = workspace.scope_dir(workspace_root, selected)
    if (
        base.is_symlink()
        or (base / "_meta").is_symlink()
        or (base / "_meta/lint-report.md").is_symlink()
    ):
        raise workspace.WorkspaceError("report destination must not be a symbolic link")
    manifest = workspace.load(base / workspace.FLAT_MANIFEST)
    docs = discover(base, manifest.get("ignore_folders") or [])
    defined = definitions_for(docs, selected)
    for other in workspace.list_scopes(workspace_root):
        if other != selected:
            defined.update(
                definitions_for(discover(workspace.scope_dir(workspace_root, other)), other)
            )
    registry_path = base / "_meta/id-registry.md"
    registry = tables.Table(list(schema.REGISTRY_COLUMNS))
    extra = []
    if registry_path.exists():
        try:
            registry = tables.parse(registry_path.read_text(encoding="utf-8")).table
            if registry is None or registry.header != schema.REGISTRY_COLUMNS:
                raise tables.TableError("registry columns differ from the shared schema")
        except (tables.TableError, UnicodeError) as exc:
            registry = tables.Table(list(schema.REGISTRY_COLUMNS))
            extra.append(Finding("L-001", "draft", "error", "_meta/id-registry.md", 1, str(exc)))
    # A reserved registry row is a definition even before its draft exists, so referencing a
    # sibling reservation does not fail L-004. Withdrawn and superseded rows do not define.
    defined.update(registry_definitions(registry, selected))
    ctx = Context(
        base,
        selected,
        gate,
        workspace.mode_of(workspace_root) == "program",
        docs,
        manifest,
        defined,
        registry,
    )
    load_waivers(ctx)
    findings = sorted(
        [*collect(ctx), *extra], key=lambda f: (f.path, f.line, f.rule, f.subject, f.msg)
    )
    report = base / "_meta/lint-report.md"
    fsio.atomic_write(report, report_text(ctx, findings))
    errors = sum(f.sev == "error" and not f.waiver for f in findings)
    return (GATES[gate] if errors else 0), {
        "scope": selected,
        "gate": gate,
        "errors": errors,
        "report": "_meta/lint-report.md",
        "findings": [asdict(f) for f in findings],
        "waivers": [list(w) for w in ctx.waivers],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", required=True, help="workspace root or directory inside a project"
    )
    parser.add_argument("--scope", help="explicit scope; required at an ambiguous program root")
    parser.add_argument("--gate", choices=GATES, default="review")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--explain", metavar="L-NNN", help="print what one rule checks and exit")
    args = parser.parse_args(argv)
    if args.explain:
        if args.explain not in RULE_HELP:
            print(f"unknown rule {args.explain}", file=sys.stderr)
            return 2
        print(f"{args.explain}: {RULE_HELP[args.explain]}")
        return 0
    try:
        code, data = run(args.root, args.gate, args.scope)
        if args.format == "json":
            print(json.dumps(data, ensure_ascii=False, sort_keys=True))
        else:
            print(
                f"{data['scope']} {data['gate']}: {data['errors']} blocking error(s); "
                f"{data['report']}"
            )
            for f in data["findings"]:
                print(
                    f"{f['path']}:{f['line']}: {f['rule']} {f['sev']} {f['msg']}"
                    + (f" [waived: {f['waiver']}]" if f["waiver"] else "")
                )
        return code
    except Exception as exc:
        print(
            f"LINT FAILED CLOSED: {type(exc).__name__}: {exc}; no passing verdict is available",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
