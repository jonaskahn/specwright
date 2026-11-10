#!/usr/bin/env python3
"""Reject active content and network references before sharing a diagram.

Exit codes: 0 clean, 1 findings, 2 usage or unreadable input.
"""

import argparse
import html
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
        sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
        break

from check_borders import paths_for  # noqa: E402

FORBIDDEN = re.compile(
    r"https?\s*:|<\s*/?\s*(?:script|link|iframe|object|embed)\b|@import\b|"
    r"@font-face\b|(?:src|href)\s*=\s*['\"]?\s*//|url\(\s*['\"]?\s*//|"
    r"<\s*image\b|<\s*img\b|\bon\w+\s*=|javascript\s*:",
    re.I,
)


def check_text(text):
    # Decode entities so encoded URLs cannot evade the offline boundary.
    decoded = html.unescape(text)
    return [
        (decoded.count("\n", 0, m.start()) + 1, m.group(0)) for m in FORBIDDEN.finditer(decoded)
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    try:
        findings = [
            f"{path}:{line}: OFFLINE forbidden {token}"
            for path in paths_for(args.paths)
            for line, token in check_text(path.read_text(encoding="utf-8"))
        ]
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
