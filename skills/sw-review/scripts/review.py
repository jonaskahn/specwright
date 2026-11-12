#!/usr/bin/env python3
"""Accept a draft in plain words, or verify and promote it on formal sign-off evidence.

`accept` is the default path: it records the owner's acceptance bound to the draft hash and needs
no approver or URL, so it works only when the project's sign-off is optional. `verify` and
`promote` check a configured approver's evidence and apply whatever the sign-off setting.

Exit codes: 0 valid, 2 invalid evidence or usage. `promote` and `accept` write the draft.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import fsio, hashing, review  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["accept", "verify", "promote"])
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--author", help="the approver's account ID (verify, promote)")
    parser.add_argument("--role", help="the approver's role in the manifest (verify, promote)")
    parser.add_argument("--name", help="the approver's name in the manifest (verify, promote)")
    parser.add_argument("--url", help="evidence URL (verify, promote)")
    parser.add_argument(
        "--kind", choices=sorted(review.KINDS), help="evidence kind (verify, promote)"
    )
    parser.add_argument(
        "--hash",
        help="accept only if the draft still has this hash, as shown in the batch table (accept)",
    )
    parser.add_argument("--body", default="")
    parser.add_argument(
        "--session-ref", default="", help="chat or meeting evidence: session or minutes reference"
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "accept":
            if args.hash:
                now = hashing.draft_hash(args.draft.read_text(encoding="utf-8"))
                if not now.removeprefix("sha256:").startswith(args.hash.removeprefix("sha256:")):
                    raise review.ApprovalError(
                        f"the draft changed since it was shown (now {hashing.short(now)}); "
                        "review it again before accepting"
                    )
            updated = review.accept(args.draft, args.scope_id, args.manifest)
            fsio.atomic_write(args.draft, updated)
            digest = hashing.short(hashing.draft_hash(updated))
            print(json.dumps({"status": "ready-to-publish", "accepted": True, "sha256": digest}))
            return 0
        missing = [f for f in ("author", "role", "name", "url", "kind") if not getattr(args, f)]
        if missing:
            parser.error("verify and promote need " + ", ".join("--" + f for f in missing))
        evidence = review.Evidence(
            args.kind,
            args.author,
            args.url,
            args.body,
            role=args.role,
            name=args.name,
            session_ref=args.session_ref,
        )
        result = review.verify_evidence(
            args.draft.read_text(encoding="utf-8"), args.scope_id, args.manifest, evidence
        )
        if args.command == "promote":
            updated = review.promote(args.draft, args.scope_id, args.manifest, evidence)
            fsio.atomic_write(args.draft, updated)
        print(json.dumps(result))
        return 0
    except (review.ApprovalError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
