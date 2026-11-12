"""Verify human approval evidence and promote only a current, reviewed draft."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from kitlib import frontmatter, hashing, miniyaml

MARKER = re.compile(r"\[sw:approve ([A-Z]{2,5}:FEAT-\d{3}) sha256:([0-9a-f]{12})\]")
SAFE_URL = re.compile(r"^https://[^\s]+$")


class ApprovalError(ValueError):
    """Evidence is absent, unverifiable or bound to another draft."""


@dataclass
class Evidence:
    kind: str  # comment, transition or pr
    author: str
    url: str
    body: str = ""
    verified: bool = True


def approvers(manifest: Path) -> set[str]:
    data = miniyaml.loads(manifest.read_text(encoding="utf-8"))
    return {str(person.get("account_id")) for person in data.get("approvers") or []}


def marker_for(draft: str, scope_id: str) -> str:
    return f"[sw:approve {scope_id} sha256:{hashing.short(hashing.draft_hash(draft))}]"


def verify_evidence(draft: str, scope_id: str, manifest: Path, evidence: Evidence) -> dict:
    """Accept only a configured approver, an HTTPS reference and a matching draft hash."""
    if not evidence.verified:
        raise ApprovalError("evidence identity has not been verified")
    if evidence.kind not in {"comment", "transition", "pr"}:
        raise ApprovalError("unknown evidence kind")
    if not SAFE_URL.match(evidence.url):
        raise ApprovalError("evidence URL must be https")
    if evidence.author not in approvers(manifest):
        raise ApprovalError("author is not a configured approver")
    if evidence.kind == "comment":
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("draft", type=Path)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--kind", choices=["comment", "transition", "pr"], required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        draft = args.draft.read_text(encoding="utf-8")
        result = verify_evidence(
            draft,
            args.scope_id,
            args.manifest,
            Evidence(args.kind, args.author, args.url, args.body),
        )
        if args.apply:
            from kitlib import fsio

            fsio.atomic_write(
                args.draft,
                promote(
                    args.draft,
                    args.scope_id,
                    args.manifest,
                    Evidence(args.kind, args.author, args.url, args.body),
                ),
            )
        print(json.dumps(result))
        return 0
    except (ApprovalError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
