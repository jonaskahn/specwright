#!/usr/bin/env python3
"""Scan sensitive text without disclosing values in reports.

Exit codes: 0 no secrets (PII may warn), or a redacted copy that scans clean; 1 secrets found
(without --redact) or still found in the redacted copy; 2 invalid arguments, unreadable input or
unsafe output. Stdout is JSON data.

Personal-data matches inside a front matter block and inside plain hashes (hex runs of 24 or more
characters) are not reported. Secrets are always reported. A reviewed documented example, a sample
value in a policy text, is allowed only through a named row in the decisions file (--decisions),
and never for a secret.
"""

from __future__ import annotations

import argparse
import json
import re
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

from kitlib import frontmatter, fsio, hashing, scanlog  # noqa: E402

PATTERNS = (
    ("atlassian-token", True, r"ATATT[0-9A-Za-z_\-=]{20,}"),
    ("aws-key", True, r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    (
        "pem-key",
        True,
        r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----.*?-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----",
    ),
    ("jwt", True, r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    ("password", True, r"(?i:\bpassword\s*[:=]\s*)(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s,;]+)"),
    ("email", False, r"(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("vn-mobile", False, r"(?<!\d)(?:0|\+84|84)[ .-]?[35789](?:[ .-]?\d){8}(?!\d)"),
    ("cccd", False, r"(?<!\d)\d{12}(?!\d)"),
    ("card", False, r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)"),
)


def luhn(value: str) -> bool:
    digits = [int(c) for c in value if c.isascii() and c.isdigit()]
    if not 13 <= len(digits) <= 19 or len(set(digits)) == 1:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        doubled = digit * 2 if index % 2 else digit
        total += doubled - 9 if doubled > 9 else doubled
    return total % 10 == 0


HASH_RUN = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{24,}(?![0-9A-Za-z])")


def _header_length(text: str) -> int:
    """Characters taken by a leading front matter block, or 0."""
    parsed = frontmatter.parse(text)
    return len(text) - len(parsed.body) if parsed.fm is not None else 0


def scan(text: str, allowed: frozenset[tuple[int, str]] = frozenset()) -> list[dict]:
    """Retain offsets, not values, so reports cannot accidentally serialize a secret.

    `allowed` holds `(line, type)` pairs a reviewer accepted as documented examples; only
    personal-data findings can be allowed.
    """
    findings = []
    header = _header_length(text)
    hashes = [(m.start(), m.end()) for m in HASH_RUN.finditer(text)]
    for kind, secret, pattern in PATTERNS:
        for match in re.finditer(pattern, text, re.S):
            if "[REDACTED:" in match.group():
                continue
            if kind == "card" and not luhn(match.group()):
                continue
            if not secret and match.start() < header:
                continue  # kit-written header fields are not personal data
            if not secret and any(s <= match.start() and match.end() <= e for s, e in hashes):
                continue  # a plain hash is not a card or an ID number
            if not secret and (text.count("\n", 0, match.start()) + 1, kind) in allowed:
                continue
            findings.append(
                {
                    "type": kind,
                    "secret": secret,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return sorted(findings, key=lambda item: (item["start"], -item["end"]))


def redact(text: str, findings: list[dict]) -> str:
    """Merge overlaps so nested PII cannot leave a private-key fragment behind."""
    result, cursor = [], 0
    for item in findings:
        start, end = item["start"], item["end"]
        if start < cursor:
            if end > cursor:
                cursor = end
            continue
        result.extend((text[cursor:start], "[REDACTED:" + item["type"] + "]"))
        cursor = end
    return "".join(result) + text[cursor:]


def report(findings: list[dict]) -> list[dict]:
    # Even short passwords must not be reconstructable from a masked tail.
    return [
        {
            "type": f["type"],
            "line": f["line"],
            "severity": "secret" if f["secret"] else "warning",
            "masked_tail": "****",
        }
        for f in findings
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--redact", action="store_true", help="replace findings with typed markers")
    parser.add_argument("--out", type=Path, help="redacted copy; defaults to the input text file")
    parser.add_argument(
        "--decisions", type=Path, help="scan-decisions.tsv with reviewed documented examples"
    )
    args = parser.parse_args(argv)
    if args.out and not args.redact:
        parser.error("--out requires --redact")
    try:
        text = args.file.read_text(encoding="utf-8")
        digest = hashing.bytes_hash(args.file.read_bytes())
        allowed = (
            scanlog.allowed(scanlog.read(args.decisions), digest) if args.decisions else frozenset()
        )
        findings = scan(text, allowed)
        leftover = findings
        markers = 0
        if args.redact:
            target = (args.out or args.file).resolve()
            if "raw" in target.parts:
                raise ValueError("raw originals cannot be redacted in place")
            clean_text = redact(text, findings)
            fsio.atomic_write(target, clean_text)
            leftover = scan(clean_text, allowed)
            markers = clean_text.count("[REDACTED:")
        print(
            json.dumps(
                {
                    "findings": report(findings),
                    "redacted": args.redact,
                    "source_sha256": digest,
                    "redaction_markers": markers,
                    "clean": not any(f["secret"] for f in leftover),
                }
            )
        )
        return 1 if any(f["secret"] for f in leftover) else 0
    except (OSError, UnicodeError, ValueError):
        print("error: cannot read UTF-8 input or write a safe redacted output", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
