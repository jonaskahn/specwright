#!/usr/bin/env python3
"""Verify approval evidence or promote one draft after it passes.

Exit codes: 0 valid, 2 invalid evidence or usage. Only --apply writes the draft.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
        sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
        break

from kitlib import fsio, review  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["verify", "promote"])
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--scope-id", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--kind", choices=["comment", "transition", "pr"], required=True)
    parser.add_argument("--body", default="")
    args = parser.parse_args(argv)
    try:
        evidence = review.Evidence(args.kind, args.author, args.url, args.body)
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
