"""Verify human approval evidence and promote only a current, reviewed draft."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from kitlib import frontmatter, hashing, miniyaml, schema, workspace

MARKER = re.compile(r"\[sw:approve ([A-Z]{2,5}:FEAT-\d{3}) sha256:([0-9a-f]{12})\]")
SAFE_URL = re.compile(r"^https://[^\s]+$")
# The owner's plain-words acceptance, bound to the draft hash:
# `self | accept | sha256:<12> | <date>`.
ACCEPT_LINE = re.compile(
    r"^self \| accept \| sha256:([0-9a-f]{12}) \| \d{4}-\d{2}-\d{2}(?: #\d+)?$"
)
TERMINAL = {"withdrawn", "superseded", "published", "ready-for-dev"}


class ApprovalError(ValueError):
    """Evidence is absent, unverifiable or bound to another draft."""


KINDS = {"comment", "transition", "pr", "chat", "meeting"}
# Chat and meeting evidence is the weakest: a project opts in and the reference must be auditable.
OPT_IN = {"chat", "meeting"}


@dataclass
class Evidence:
    kind: str  # comment, transition, pr, chat or meeting
    author: str  # the approver's account ID
    url: str
    body: str = ""
    verified: bool = True
    role: str = ""
    name: str = ""
    session_ref: str = ""


def approver_records(manifest: Path) -> list[dict]:
    data = miniyaml.loads(manifest.read_text(encoding="utf-8"))
    return [dict(person) for person in data.get("approvers") or []]


def approvers(manifest: Path) -> set[str]:
    return {str(person.get("account_id")) for person in approver_records(manifest)}


def allowed_kinds(manifest: Path) -> list[str]:
    data = miniyaml.loads(manifest.read_text(encoding="utf-8"))
    kinds = (data.get("evidence") or {}).get("allowed_kinds")
    return [str(k) for k in kinds] if kinds else list(schema.DEFAULT_EVIDENCE_KINDS)


def marker_for(draft: str, scope_id: str) -> str:
    return f"[sw:approve {scope_id} sha256:{hashing.short(hashing.draft_hash(draft))}]"


def verify_evidence(draft: str, scope_id: str, manifest: Path, evidence: Evidence) -> dict:
    """Accept only a configured approver, an HTTPS reference and a matching draft hash."""
    if not evidence.verified:
        raise ApprovalError("evidence identity has not been verified")
    if evidence.kind not in KINDS:
        raise ApprovalError("unknown evidence kind")
    if not SAFE_URL.match(evidence.url):
        raise ApprovalError("evidence URL must be https")
    person = next(
        (p for p in approver_records(manifest) if str(p.get("account_id")) == evidence.author),
        None,
    )
    if person is None:
        raise ApprovalError("author is not a configured approver")
    for field, given in (("role", evidence.role), ("name", evidence.name)):
        if given and str(person.get(field, "")).casefold() != given.strip().casefold():
            raise ApprovalError(f"{field} does not match the configured approver")
    if evidence.kind in OPT_IN:
        if evidence.kind not in allowed_kinds(manifest):
            raise ApprovalError(f"this project does not accept {evidence.kind} evidence")
        if not evidence.session_ref.strip():
            raise ApprovalError(
                f"{evidence.kind} evidence needs a session reference to audit later"
            )
    if evidence.kind in ("comment", *OPT_IN):
        match = MARKER.search(evidence.body)
        if not match:
            raise ApprovalError("comment lacks an approval marker")
        if match.group(1) != scope_id:
            raise ApprovalError("approval marker refers to another feature")
        if match.group(2) != hashing.short(hashing.draft_hash(draft)):
            raise ApprovalError("approval marker hash does not match the current draft")
    elif evidence.kind == "pr" and not re.search(r"/pull/\d+", evidence.url):
        raise ApprovalError("PR evidence must name a pull request")
    elif evidence.kind == "transition" and "transition" not in evidence.body.lower():
        raise ApprovalError("transition evidence must name the transition")
    digest = hashing.short(hashing.draft_hash(draft))
    signoff = f"{evidence.author} | {evidence.kind} | sha256:{digest} | {evidence.url}"
    if evidence.kind in OPT_IN:
        signoff += f" | session:{' '.join(evidence.session_ref.split())}"
    return {"status": "ready-to-publish", "signoff": signoff, "verified": evidence.verified}


def _guard(manifest: Path, scope_id: str) -> dict | None:
    """Shared checks before a draft becomes accepted; returns (history, latest invalidation)."""
    from kitlib import lifecycle

    history = lifecycle.decisions(manifest.parent, scope_id)
    latest = next((r for r in reversed(history) if r["action"] != "set-destination"), {})
    if latest.get("action") == "reopen-shape":
        raise ApprovalError("accept the reopened feature slice before review")
    if (manifest.parent / "_meta/lifecycle-pending.json").exists():
        raise ApprovalError("incomplete lifecycle transaction requires recovery")
    invalidation = next(
        (r for r in reversed(history) if r["action"] in lifecycle.INVALIDATES), None
    )
    return invalidation


def _record(text: str, line: str, invalidation: dict | None) -> str:
    fm, body = frontmatter.split(text)
    if invalidation:
        fm["approval_after"] = invalidation["id"]
    fm["status"] = "ready-to-publish"
    fm["signoffs"] = [*(fm.get("signoffs") or []), line]
    return frontmatter.render(fm, body)


def promote(draft_path: Path, scope_id: str, manifest: Path, evidence: Evidence) -> str:
    """Write status and signoff only after evidence passes; keep the body and hash stable."""
    original = draft_path.read_text(encoding="utf-8")
    result = verify_evidence(original, scope_id, manifest, evidence)
    invalidation = _guard(manifest, scope_id)
    if invalidation and result["signoff"] in (invalidation.get("signoffs") or []):
        raise ApprovalError("approval was invalidated; provide fresh evidence")
    return _record(original, result["signoff"], invalidation)


def accept(draft_path: Path, scope_id: str, manifest: Path, today: date | None = None) -> str:
    """The owner's plain-words acceptance, bound to the current draft hash.

    It needs no approver and no URL, so it is allowed only when sign-off is optional. The line
    goes stale the moment the content changes, exactly like a formal sign-off.
    """
    if workspace.governance_of(workspace.load(manifest))["signoff"] != "optional":
        raise ApprovalError("sign-off is required here; accept needs a configured approver")
    original = draft_path.read_text(encoding="utf-8")
    fm, _ = frontmatter.split(original)
    if str(fm.get("status")) in TERMINAL:
        raise ApprovalError(
            f"a {fm.get('status')} story changes only through a change request, not an accept"
        )
    report = manifest.parent / "_meta/lint-report.md"
    if not report.is_file() or "0 blocking error(s)" not in report.read_text(encoding="utf-8"):
        raise ApprovalError("a passing lint gate is required before accepting")
    invalidation = _guard(manifest, scope_id)
    digest = hashing.short(hashing.draft_hash(original))
    line = f"self | accept | sha256:{digest} | {(today or date.today()).isoformat()}"
    spent = {*(fm.get("signoffs") or []), *((invalidation or {}).get("signoffs") or [])}
    n = 1
    candidate = line
    while candidate in spent:  # a fresh confirmation after a return is never the old line again
        n += 1
        candidate = f"{line} #{n}"
    return _record(original, candidate, invalidation)


def line_counts(line: object, digest: str, mode: str) -> bool:
    """True when one signoffs entry binds this content under the given sign-off mode."""
    text = str(line)
    if digest in text and "https://" in text:
        return True
    match = ACCEPT_LINE.match(text)
    return mode == "optional" and bool(match) and match.group(1) == digest


def approval_label(text: str, signoffs: list, mode: str) -> str:
    """`signed-off`, `accepted`, `needs-signoff`, `stale` or `unknown` for one draft's lines."""
    if not signoffs:
        return "unknown"
    digest = hashing.short(hashing.draft_hash(text))
    if any(digest in str(s) and "https://" in str(s) for s in signoffs):
        return "signed-off"
    accepted = any((m := ACCEPT_LINE.match(str(s))) and m.group(1) == digest for s in signoffs)
    if accepted:
        return "accepted" if mode == "optional" else "needs-signoff"
    return "stale"


def stale(draft: str, signoffs: list[str], mode: str = "required") -> bool:
    expected = hashing.short(hashing.draft_hash(draft))
    return not any(line_counts(line, expected, mode) for line in signoffs)
