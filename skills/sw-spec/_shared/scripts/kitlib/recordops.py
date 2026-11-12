"""Create and change questions, decisions, reservations and registry rows through one path.

Every operation validates first and builds a plan, so a dry run shows exactly what would be
written. A real run logs an intent, writes atomically, rebuilds the derived trace and graph, and
logs the result; a failure undoes what it wrote. Registry cells go through the ownership check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from kitlib import (
    candidates,
    cite,
    epics,
    frontmatter,
    fsio,
    hashing,
    ids,
    rtm,
    schema,
    workspace,
    writelog,
)


class RecordError(ValueError):
    """The request is invalid; nothing was written."""


class AskError(RecordError):
    """A human must supply something first (for example the approvers)."""


@dataclass
class Ctx:
    root: Path
    scope: str
    skill: str
    today: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def base(self) -> Path:
        return workspace.scope_dir(self.root, self.scope)

    @property
    def log(self) -> Path:
        return self.base / "_meta/write-log.md"

    @property
    def registry(self) -> Path:
        return self.base / "_meta/id-registry.md"


@dataclass
class Plan:
    summary: list[str] = field(default_factory=list)
    creates: dict[Path, str] = field(default_factory=dict)
    rewrites: dict[Path, str] = field(default_factory=dict)
    registry: list[tuple[str, dict[str, str]]] = field(default_factory=list)
    made: list[str] = field(default_factory=list)
    taken: list[str] = field(default_factory=list)

    def next_id(self, prefix: str, width: int = 3) -> str:
        identity = ids.next_id(prefix, self.taken, width)
        self.taken.append(identity)
        self.made.append(identity)
        return identity


def new_plan(ctx: Ctx) -> Plan:
    return Plan(taken=ids.taken_ids(ctx.base))


# ---- validation -------------------------------------------------------------------------------


def _line(value: str, label: str, limit: int = 160) -> str:
    text = " ".join(str(value).split())
    if not text or len(text) > limit:
        raise RecordError(f"{label} must be one line of 1..{limit} characters")
    return text


def _known(ctx: Ctx) -> set[str]:
    entities, _ = rtm.scan(ctx.root)
    known = set(entities)
    registry = rtm.read_table(ctx.registry, list(schema.REGISTRY_COLUMNS)).table
    known.update(row[0] for row in registry.rows)
    return known


def affects_list(ctx: Ctx, values: list[str], label: str = "affects") -> list[str]:
    """Qualified-if-foreign IDs, each of which must exist or be reserved."""
    if not values:
        raise RecordError(f"{label} needs at least one item")
    known = _known(ctx)
    out = []
    for raw in values:
        ref = ids.parse_ref(ids.story_alias(raw.strip()))
        if ref is None:
            raise RecordError(f"{label}: '{raw}' is not a spec ID")
        key = rtm.qualify(str(ref), ctx.scope)
        if key not in known:
            raise RecordError(f"{label}: {key} is not defined or reserved")
        out.append(ref.id if key.split(":")[0] == ctx.scope else key)
    return list(dict.fromkeys(out))


def citations(ctx: Ctx, values: list[str], quote: str = "") -> tuple[list[str], list[str]]:
    """Stamped citations and the exact cited text; a dangling or non-matching one is refused."""
    sources = cite.Sources(ctx.base)
    stamped, blocks = [], []
    expanded: list[str] = []
    for raw in values:
        if candidates.ITEM_KEY.match(raw.strip()):
            try:
                expanded.extend(candidates.item_citations(ctx.base, raw))
            except ValueError as exc:
                raise RecordError(str(exc)) from None
        else:
            expanded.append(raw)
    for raw in expanded:
        c = cite.parse_one(raw)
        found = [p for p in cite.problems(sources, c.text()) if p.severity == "error"]
        if found:
            raise RecordError(found[0].message)
        stamped.append(cite.stamp(sources, c))
        blocks.append(cite.quote(sources, c))
    if quote.strip():
        wanted = cite.normalize(quote)
        if not any(wanted in cite.normalize(block) for block in blocks):
            raise RecordError("the quotation is not inside the cited lines")
    return stamped, blocks


def decided_by(ctx: Ctx, role: str, name: str, account_id: str = "") -> dict[str, str]:
    """The manifest's own spelling of an approver; blank, unknown or unlisted people are refused."""
    approvers = workspace.approver_list(ctx.root, ctx.scope)
    if not approvers:
        raise AskError(
            "no approvers are recorded; add them first: workspace.py approvers add "
            "--role <role> --name <name> --account-id <id>"
        )
    if not role.strip() or not name.strip():
        raise RecordError("a decision needs the decider's role and name")
    for person in approvers:
        same_role = str(person.get("role", "")).casefold() == role.strip().casefold()
        same_name = str(person.get("name", "")).casefold() == name.strip().casefold()
        same_id = not account_id or person.get("account_id") == account_id.strip()
        if same_role and same_name and same_id:
            return {
                "role": str(person["role"]),
                "name": str(person["name"]),
                "account_id": str(person.get("account_id", "")),
            }
    raise RecordError(f"{name} ({role}) is not in the manifest approvers")


def evidence(ctx: Ctx, kind: str, ref: str) -> tuple[str, str]:
    if kind not in schema.EVIDENCE_KINDS:
        raise RecordError(f"evidence kind must be one of {', '.join(schema.EVIDENCE_KINDS)}")
    if kind not in workspace.evidence_kinds(ctx.root, ctx.scope):
        raise RecordError(f"this project does not accept {kind} evidence (manifest evidence)")
    ref = ref.strip()
    if not ref or ref.lower() in ("tbd", "unknown", "none", "n/a"):
        raise RecordError("evidence_ref is required: a URL, ticket, minutes ID or file hash")
    if kind in ("url", "chat") and not ref.startswith("https://"):
        raise RecordError(f"{kind} evidence needs an https permalink")
    return kind, ref


def _item(raw: str) -> tuple[str, list[str]]:
    """`Title|alias1,alias2` into a title and its aliases."""
    title, _, rest = raw.partition("|")
    aliases = [a.strip() for a in rest.split(",") if a.strip()]
    return _line(title, "item title", 100), aliases


def alias_owners(ctx: Ctx) -> dict[str, str]:
    owners: dict[str, str] = {}
    entities, _ = rtm.scan(ctx.root)
    for key, entity in entities.items():
        value = entity.fm.get("aliases") if isinstance(entity.fm, dict) else None
        for alias in value if isinstance(value, list) else []:
            owners[str(alias).casefold()] = key
    registry = rtm.read_table(ctx.registry, list(schema.REGISTRY_COLUMNS)).table
    for row in registry.rows:
        for alias in registry.value(row[0], "Aliases").split("|"):
            if alias.strip():
                owners.setdefault(alias.strip().casefold(), row[0])
    return owners


def _check_aliases(ctx: Ctx, aliases: list[str], taken: dict[str, str]) -> None:
    for alias in aliases:
        owner = taken.get(alias.casefold())
        if owner:
            raise RecordError(f"alias '{alias}' already names {owner}")
        taken[alias.casefold()] = "this request"


# ---- questions --------------------------------------------------------------------------------


def question_new(
    ctx: Ctx,
    title: str,
    affects: list[str],
    owner: str,
    due: str = "",
    raised_from: list[str] | None = None,
    quote: str = "",
    why: str = "",
    options: list[str] | None = None,
    default: str = "",
    blocking: bool = True,
    status: str = "proposed",
) -> Plan:
    if status not in ("proposed", "open"):
        raise RecordError("a new question starts as proposed or open")
    title = _line(title, "title", 120)
    owner = _line(owner, "owner", 60)
    if due and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
        raise RecordError("due must be YYYY-MM-DD")
    targets = affects_list(ctx, affects)
    stamped, blocks = citations(ctx, raised_from or [], quote)
    plan = new_plan(ctx)
    identity = plan.next_id("Q")
    fm: dict[str, Any] = {
        "id": identity,
        "type": "q",
        "scope": ctx.scope,
        "title": title,
        "aliases": [],
        "status": status,
        "blocking": blocking,
        "affects": targets,
        "owner": owner,
        "due": due or "Unknown",
        "raised_from": stamped,
        "sources": sorted({cite.parse_one(s).source for s in stamped}),
        "supersedes": [],
        "created": ctx.today,
    }
    body = [f"## Question\n\n{title}\n"]
    if stamped:
        body.append("## Evidence\n")
        for citation, text in zip(stamped, blocks, strict=True):
            quoted = "\n".join("> " + line for line in text.splitlines())
            body.append(f"{citation}\n\n{quoted}\n")
    body.append(f"## Why it matters\n\n{why.strip() or 'Not yet assessed.'}\n")
    letters = [chr(ord("A") + i) for i in range(len(options or []))]
    listed = [f"- {x}) {text}" for x, text in zip(letters, options or [], strict=True)]
    body.append("## Options\n\n" + ("\n".join(listed) if listed else "- Not yet listed.") + "\n")
    body.append(f"Default if unanswered: {default.strip() or 'stay unresolved; not approval'}.\n")
    path = ctx.base / "records" / ids.record_filename(identity, title)
    plan.creates[path] = frontmatter.render(fm, "\n".join(body))
    plan.summary.append(f"create {path.relative_to(ctx.base).as_posix()} ({status})")
    return plan


def _record(ctx: Ctx, identity: str) -> tuple[Path, dict[str, Any], str]:
    path = ids.find_record(ctx.base / "records", identity)
    if path is None:
        raise RecordError(f"no record {identity} in records/")
    fm, body = frontmatter.split(path.read_text(encoding="utf-8"))
    if fm is None:
        raise RecordError(f"{path.name} has no front matter")
    return path, fm, body


def question_withdraw(ctx: Ctx, identity: str, reason: str) -> Plan:
    path, fm, body = _record(ctx, identity)
    if fm.get("type") != "q" or fm.get("status") not in schema.OPEN_Q:
        raise RecordError(f"{identity} is not an open question")
    reason = _line(reason, "reason", 300)
    fm["status"] = "withdrawn"
    fm["withdrawn_on"] = ctx.today
    plan = new_plan(ctx)
    plan.rewrites[path] = frontmatter.render(
        fm, body.rstrip("\n") + f"\n\n## Withdrawn\n\n{reason}\n"
    )
    plan.summary.append(f"withdraw {identity}; the record and its ID stay")
    return plan


def decision_fields(
    ctx: Ctx,
    role: str,
    name: str,
    account_id: str,
    kind: str,
    ref: str,
) -> dict[str, Any]:
    who = decided_by(ctx, role, name, account_id)
    kind, ref = evidence(ctx, kind, ref)
    fields: dict[str, Any] = {
        "decided_by": who,
        "evidence_kind": kind,
        "evidence_ref": ref,
    }
    if kind == "url":
        fields["evidence_url"] = ref
    return fields


def decision_new(
    ctx: Ctx,
    title: str,
    affects: list[str],
    who: dict[str, Any],
    decision: str = "",
    context: str = "",
    supersedes: list[str] | None = None,
    answers: list[str] | None = None,
    plan: Plan | None = None,
    subtype: str = "decision",
    extra: dict[str, Any] | None = None,
) -> tuple[Plan, str]:
    title = _line(title, "title", 120)
    targets = affects_list(ctx, affects)
    plan = plan or new_plan(ctx)
    identity = plan.next_id("DEC")
    older = []
    for old in supersedes or []:
        path, old_fm, old_body = _record(ctx, old)
        if old_fm.get("type") != "dec" or old_fm.get("status") != "accepted":
            raise RecordError(f"{old} is not an accepted decision")
        old_fm["status"] = "superseded"
        plan.rewrites[path] = frontmatter.render(old_fm, old_body)
        older.append(old)
    fm: dict[str, Any] = {
        "id": identity,
        "type": "dec",
        "scope": ctx.scope,
        "title": title,
        "aliases": [],
        "subtype": subtype,
        "status": "accepted",
        **who,
        "date": ctx.today,
        "affects": targets,
        "supersedes": older,
        "created": ctx.today,
    }
    if answers:
        fm["answers"] = list(answers)
    fm.update(extra or {})
    body = (
        f"## Context\n\n{context.strip() or 'See the linked records.'}\n\n"
        f"## Decision\n\n{decision.strip() or title}\n"
    )
    path = ctx.base / "records" / ids.record_filename(identity, title)
    plan.creates[path] = frontmatter.render(fm, body)
    plan.summary.append(f"create {path.relative_to(ctx.base).as_posix()}")
    return plan, identity


def question_answer(
    ctx: Ctx, identity: str, answer: str, who: dict[str, Any], amend: list[str] | None = None
) -> Plan:
    path, fm, body = _record(ctx, identity)
    if fm.get("type") != "q" or fm.get("status") not in schema.OPEN_Q:
        raise RecordError(f"{identity} is not an open question")
    answer = answer.strip()
    if not answer:
        raise RecordError("an answer needs text")
    plan, decision = decision_new(
        ctx,
        f"Answer to {identity}: {fm.get('title', identity)}",
        [str(a) for a in fm.get("affects") or []],
        who,
        decision=answer,
        context=f"Answers {identity}.",
        answers=[identity],
    )
    fm.update({"status": "answered", "decision": decision, "answered_on": ctx.today})
    plan.rewrites[path] = frontmatter.render(fm, body.rstrip("\n") + f"\n\n## Answer\n\n{answer}\n")
    plan.summary.append(f"answer {identity} with {decision}")
    for raw in amend or []:
        parts = [p.strip() for p in raw.split("||")]
        if len(parts) != 3:
            raise RecordError("--amend is 'FEAT-001||current wording||proposed wording'")
        amendment_new(ctx, parts[0], parts[1], parts[2], decision=decision, plan=plan)
    return plan


# ---- pending amendments -----------------------------------------------------------------------


def _quoted(block: str) -> str:
    return "\n".join("> " + line for line in block.strip().splitlines())


def _story(ctx: Ctx, feat: str) -> tuple[str, str]:
    ref = ids.parse_ref(ids.story_alias(feat.strip()))
    if ref is None or not ids.matches_type("feature", ref.id):
        raise RecordError(f"'{feat}' is not a feature ID")
    path = ctx.base / "02-drafts" / f"{ref.id}.story.md"
    if not path.is_file():
        raise RecordError(f"{ref.id} has no saved story text to amend")
    return ref.id, path.read_text(encoding="utf-8")


def amendment_new(
    ctx: Ctx,
    feat: str,
    quote: str,
    proposed: str,
    decision: str = "",
    source: str = "",
    plan: Plan | None = None,
) -> tuple[Plan, str]:
    """Track a wording change that an answer implies, so it reaches the acceptance criteria."""
    feat_id, text = _story(ctx, feat)
    if not quote.strip() or not proposed.strip():
        raise RecordError("an amendment needs the current wording and the proposed wording")
    if cite.normalize(quote) not in cite.normalize(frontmatter.parse(text).body):
        raise RecordError(f"the quoted wording is not in the saved story of {feat_id}")
    if cite.normalize(quote) == cite.normalize(proposed):
        raise RecordError("the proposed wording equals the current wording")
    stamped, _ = citations(ctx, [source]) if source else ([], [])
    published = rtm.read_table(ctx.registry, list(schema.REGISTRY_COLUMNS)).table
    key = f"{ctx.scope}:{feat_id}"
    live = published.value(key, "State") == "published" or bool(published.value(key, "Jira key"))
    plan = plan or new_plan(ctx)
    identity = plan.next_id("AMD")
    title = f"Amend {feat_id}: {' '.join(quote.split()[:8])}"
    fm: dict[str, Any] = {
        "id": identity,
        "type": "amendment",
        "scope": ctx.scope,
        "title": title,
        "aliases": [],
        "status": "proposed",
        "affects": [feat_id],
        "decision": decision,
        "sources": sorted({cite.parse_one(s).source for s in stamped}),
        "supersedes": [],
        "requires_cr": live,
        "created": ctx.today,
    }
    body = (
        f"## Current wording\n\n{_quoted(quote)}\n\n## Proposed wording\n\n{_quoted(proposed)}\n\n"
        f"## Why\n\n{('Decision ' + decision + '.') if decision else 'See the linked record.'}"
        + (f" Evidence: {', '.join(stamped)}." if stamped else "")
        + "\n"
    )
    if live:
        body += "\nThis feature is already published: raise a change request before revising it.\n"
    path = ctx.base / "records" / ids.record_filename(identity, title)
    plan.creates[path] = frontmatter.render(fm, body)
    plan.summary.append(f"create {path.relative_to(ctx.base).as_posix()} for {feat_id}")
    return plan, identity


def _wording(body: str, heading: str) -> str:
    match = re.search(rf"## {heading}\n\n((?:>.*\n?)+)", body)
    return "\n".join(line[2:] for line in match.group(1).splitlines()) if match else ""


def amendment_close(ctx: Ctx, identity: str, outcome: str, reason: str = "") -> Plan:
    path, fm, body = _record(ctx, identity)
    if fm.get("type") != "amendment" or fm.get("status") != "proposed":
        raise RecordError(f"{identity} is not a proposed amendment")
    plan = new_plan(ctx)
    if outcome == "applied":
        feat_id, text = _story(ctx, str(fm["affects"][0]))
        story_body = cite.normalize(frontmatter.parse(text).body)
        if cite.normalize(_wording(body, "Current wording")) in story_body:
            raise RecordError("the draft still carries the current wording; edit it first")
        if cite.normalize(_wording(body, "Proposed wording")) not in story_body:
            raise RecordError("the draft does not carry the proposed wording yet")
        fm["applied_hash"] = hashing.draft_hash(text)
        note = f"Applied to {feat_id}; a changed draft needs fresh approval."
    else:
        note = _line(reason, "reason", 300)
    fm.update({"status": outcome, "closed_on": ctx.today})
    plan.rewrites[path] = frontmatter.render(fm, body.rstrip("\n") + f"\n\n## Outcome\n\n{note}\n")
    plan.summary.append(f"{outcome} {identity}")
    return plan


# ---- reservations and splits ------------------------------------------------------------------


def reserve_features(ctx: Ctx, items: list[str], plan: Plan | None = None) -> Plan:
    if not items:
        raise RecordError("reserve at least one feature: --item 'Title|alias1,alias2'")
    plan = plan or new_plan(ctx)
    taken = alias_owners(ctx)
    for raw in items:
        title, aliases = _item(raw)
        _check_aliases(ctx, aliases, taken)
        identity = plan.next_id("FEAT")
        cells = {"Kind": "story", "Title": title, "State": "reserved"}
        if aliases:
            cells["Aliases"] = "|".join(aliases)
        plan.registry.append((f"{ctx.scope}:{identity}", cells))
        plan.summary.append(f"reserve {ctx.scope}:{identity} '{title}'")
    return plan


def reserve_epic(ctx: Ctx, title: str, scopes: list[str] | None = None, plan: Plan | None = None):
    plan = plan or new_plan(ctx)
    try:
        identity, path, text = epics.build(ctx.base, ctx.scope, title, scopes, taken=plan.taken)
    except ValueError as exc:
        raise RecordError(str(exc)) from None
    plan.taken.append(identity)
    plan.made.append(identity)
    plan.creates[path] = text
    plan.summary.append(f"create {path.relative_to(ctx.base).as_posix()}")
    return plan, identity


def accept_split(
    ctx: Ctx,
    items: list[str],
    existing: list[str],
    epic_ids: list[str],
    new_epic: str,
    who: dict[str, Any],
) -> Plan:
    if not who.get("evidence_url"):
        raise RecordError("an accepted split needs url evidence (an https evidence_ref)")
    if not (items or existing):
        raise RecordError("name the features: --item 'Title|aliases' or --existing FEAT-NNN")
    if not (epic_ids or new_epic):
        raise RecordError("name the epic: --epic EPIC-NNN or --new-epic 'Title'")
    plan = new_plan(ctx)
    entities, _ = rtm.scan(ctx.root)
    epic_keys = []
    for raw in epic_ids:
        key = rtm.qualify(raw, ctx.scope)
        found = entities.get(key)
        if (
            not found
            or found.kind != "epic"
            or found.fm.get("status") in ("withdrawn", "superseded")
        ):
            raise RecordError(f"{raw} is not an active epic")
        epic_keys.append(key)
    if new_epic:
        plan, identity = reserve_epic(ctx, new_epic, plan=plan)
        epic_keys.append(f"{ctx.scope}:{identity}")
    before = len(plan.registry)
    if items:
        reserve_features(ctx, items, plan)
    features = [key for key, _ in plan.registry[before:]]
    known = _known(ctx)
    for raw in existing:
        key = rtm.qualify(ids.story_alias(raw), ctx.scope)
        if key not in known or ":FEAT-" not in key:
            raise RecordError(f"{raw} is not a defined or reserved feature")
        features.append(key)
    plan = _split_decision(ctx, plan, who, epic_keys, features)
    return plan


def _split_decision(ctx: Ctx, plan: Plan, who: dict[str, Any], epic_keys: list[str], features):
    """The accepted-split decision; its targets are only now reserved, so it skips the lookup."""
    identity = plan.next_id("DEC")
    title = "Accepted split: " + ", ".join(k.split(":")[1] for k in epic_keys)
    fm = {
        "id": identity,
        "type": "dec",
        "scope": ctx.scope,
        "title": title,
        "aliases": [],
        "subtype": "accepted-split",
        "status": "accepted",
        **who,
        "date": ctx.today,
        "affects": [*epic_keys, *features],
        "supersedes": [],
        "epics": epic_keys,
        "features": features,
        "created": ctx.today,
    }
    body = (
        "## Context\n\nFeatures grouped under the named epics.\n\n"
        "## Decision\n\nThe named decider accepted this split.\n"
    )
    path = ctx.base / "records" / ids.record_filename(identity, title)
    plan.creates[path] = frontmatter.render(fm, body)
    plan.summary.append(f"create {path.relative_to(ctx.base).as_posix()}")
    return plan


def register_group(ctx: Ctx, group: str) -> tuple[list[str], list[str]]:
    """`(new item args, existing feature IDs)` for every legacy item of a register group."""
    from kitlib import baseline, index

    rows = index.read_register(ctx.base / baseline.REGISTER)
    if rows is None:
        raise RecordError("no legacy register; run baseline.py import-register first")
    wanted = [r for r in rows if (r.get("group") or "ungrouped") == group]
    if not wanted:
        raise RecordError(f"the register has no group '{group}'")
    owners = alias_owners(ctx)
    items, existing = [], []
    for row in wanted:
        owner = owners.get(row["legacy_id"].casefold(), "")
        if ":FEAT-" in owner:
            existing.append(owner.split(":")[1])
        else:
            items.append(baseline.item_arg(row))
    return items, existing


def register(ctx: Ctx, key: str, cells: dict[str, str]) -> Plan:
    ref = ids.parse_ref(key)
    if ref is None:
        raise RecordError(f"'{key}' is not a spec ID")
    qualified = rtm.qualify(str(ref), ctx.scope)
    if qualified.split(":")[0] != ctx.scope:
        raise RecordError("register writes only rows of the selected project")
    plan = new_plan(ctx)
    plan.registry.append((qualified, cells))
    plan.summary.append(f"set {', '.join(sorted(cells))} on {qualified}")
    return plan


# ---- execution --------------------------------------------------------------------------------


def execute(ctx: Ctx, plan: Plan, action: str, target: str) -> list[str]:
    """Write the plan under one logged operation; undo everything if any step fails."""
    created: list[Path] = []
    saved: dict[Path, bytes | None] = {}
    registry_before = ctx.registry.read_bytes() if ctx.registry.is_file() else None
    warnings: list[str] = []
    with writelog.operation(ctx.log, ctx.skill, action, target) as op:
        try:
            for path, text in plan.creates.items():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("x", encoding="utf-8", newline="") as handle:
                    handle.write(text)
                created.append(path)
                op.wrote(path)
            for path, text in plan.rewrites.items():
                saved[path] = path.read_bytes()
                fsio.atomic_write(path, text)
                op.wrote(path)
            for key, cells in plan.registry:
                rtm.registry_upsert(ctx.registry, key, cells, ctx.skill)
            if plan.registry:
                op.wrote(ctx.registry)
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            for path, data in saved.items():
                if data is not None:
                    path.write_bytes(data)
            if registry_before is not None:
                ctx.registry.write_bytes(registry_before)
            raise
    try:
        from kitlib import graph

        rtm.rebuild(ctx.root, ctx.scope)
        graph.build(ctx.root, ctx.scope)
    except (ValueError, OSError) as exc:
        warnings.append(f"derived files not rebuilt: {exc}")
    return warnings
