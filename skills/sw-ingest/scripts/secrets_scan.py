#!/usr/bin/env python3
"""Scan sensitive text without disclosing values in reports.

Exit codes: 0 no secrets (PII may warn), 1 secrets found even after redaction,
2 invalid arguments, unreadable input or unsafe output. Stdout is JSON data.
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

from kitlib import fsio  # noqa: E402

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


def scan(text: str) -> list[dict]:
    """Retain offsets, not values, so reports cannot accidentally serialize a secret."""
    findings = []
    for kind, secret, pattern in PATTERNS:
        for match in re.finditer(pattern, text, re.S):
            if "[REDACTED:" in match.group():
                continue
            if kind == "card" and not luhn(match.group()):
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
    args = parser.parse_args(argv)
    if args.out and not args.redact:
        parser.error("--out requires --redact")
    try:
        text = args.file.read_text(encoding="utf-8")
        findings = scan(text)
        if args.redact:
            target = (args.out or args.file).resolve()
            if "raw" in target.parts:
                raise ValueError("raw originals cannot be redacted in place")
            fsio.atomic_write(target, redact(text, findings))
        print(json.dumps({"findings": report(findings), "redacted": args.redact}))
        return 1 if any(f["secret"] for f in findings) else 0
    except (OSError, UnicodeError, ValueError):
        print("error: cannot read UTF-8 input or write a safe redacted output", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
