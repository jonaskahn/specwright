"""Verify human approval evidence and promote only a current, reviewed draft."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from kitlib import frontmatter, hashing, miniyaml, schema

MARKER = re.compile(r"\[sw:approve ([A-Z]{2,5}:FEAT-\d{3}) sha256:([0-9a-f]{12})\]")
SAFE_URL = re.compile(r"^https://[^\s]+$")


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


def promote(draft_path: Path, scope_id: str, manifest: Path, evidence: Evidence) -> str:
    """Write status and signoff only after evidence passes; keep the body and hash stable."""
    original = draft_path.read_text(encoding="utf-8")
    result = verify_evidence(original, scope_id, manifest, evidence)
    fm, body = frontmatter.split(original)
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
    if invalidation:
        if result["signoff"] in (invalidation.get("signoffs") or []):
            raise ApprovalError("approval was invalidated; provide fresh evidence")
        fm["approval_after"] = invalidation["id"]
    signoffs = list(fm.get("signoffs") or []) + [result["signoff"]]
    fm["status"] = "ready-to-publish"
    fm["signoffs"] = signoffs
    return frontmatter.render(fm, body)


def stale(draft: str, signoffs: list[str]) -> bool:
    expected = hashing.short(hashing.draft_hash(draft))
    return not any(expected in str(line) and "https://" in str(line) for line in signoffs)
