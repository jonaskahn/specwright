#!/usr/bin/env python3
"""Reject work-tracking labels, the design brief name and attribution trailers.

Usage:
  hygiene.py files [paths...]     scan files (default: staged files)
  hygiene.py message <file>       scan a commit message
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CONTENT_PATTERNS = [
    (re.compile(r"\b(?:phase|wave|milestone|task|sprint)[ _-]?\d+\b", re.I), "work-tracking label"),
    (re.compile(r"\b[mtp]-\d{1,3}\b", re.I), "work-tracking id"),
    (re.compile(r"specwright-kit-v\d", re.I), "reference to the design brief file"),
]
MESSAGE_PATTERNS = [
    *CONTENT_PATTERNS,
    (re.compile(r"^co-authored-by:", re.I | re.M), "co-author trailer"),
    (re.compile(r"generated (?:with|by)", re.I), "tool attribution"),
    (re.compile(r"^signed-off-by:", re.I | re.M), "sign-off trailer"),
]
TEXT_SUFFIXES = {".md", ".py", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".html", ".txt", ""}


def scan(text: str, patterns: list[tuple[re.Pattern[str], str]], label: str) -> list[str]:
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        for pattern, why in patterns:
            match = pattern.search(line)
            if match:
                problems.append(f"{label}:{number}: {why}: '{match.group(0)}'")
    return problems


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return [line for line in out.stdout.splitlines() if line]


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("files", "message"):
        print(__doc__, file=sys.stderr)
        return 2
    problems: list[str] = []
    if argv[0] == "message":
        problems = scan(Path(argv[1]).read_text(encoding="utf-8"), MESSAGE_PATTERNS, argv[1])
    else:
        targets = argv[1:] or staged_files()
        for name in targets:
            path = Path(name)
            if path.suffix.lower() in TEXT_SUFFIXES and path.is_file():
                problems += scan(
                    path.read_text(encoding="utf-8", errors="replace"), CONTENT_PATTERNS, name
                )
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
