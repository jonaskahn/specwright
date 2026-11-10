#!/usr/bin/env python3
"""Check implementation words in Problem and Outcome sections.

Exit codes: 0 clean, 1 leakage, 2 usage, parse or file error.
Findings are file:line data on stdout; diagnostics go to stderr.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from kitlib import frontmatter, markdown  # noqa: E402

DEFAULT_WORDS = _here.parent / "references" / "domain" / "leakage-words.md"


def load_words(path: Path = DEFAULT_WORDS) -> list[str]:
    words = [
        line[2:].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("- ")
    ]
    if not words or any(not word for word in words):
        raise ValueError("word list requires nonempty '- phrase' entries")
    return words


def check(text: str, words: list[str]) -> list[tuple[int, str]]:
    parsed = frontmatter.parse(text)
    if parsed.error:
        raise ValueError(parsed.error)
    sections = markdown.iter_sections(parsed.body, first_line=parsed.body_line)
    selected = [
        s
        for s in sections
        if s.name.casefold() in {"problem", "outcome", "smallest valuable outcome"}
    ]
    if len(selected) != 2 or sum(s.name.casefold() == "problem" for s in selected) != 1:
        raise ValueError("expected one Problem and one Smallest valuable outcome section")
    patterns = [
        (word, re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, word.split())) + r"(?!\w)", re.I))
        for word in words
    ]
    findings = []
    for section in selected:
        for number, line in section.lines:
            for word, pattern in patterns:
                if pattern.search(line):
                    findings.append((number, word))
    return sorted(set(findings))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--words", type=Path, default=DEFAULT_WORDS)
    args = parser.parse_args(argv)
    try:
        words = load_words(args.words)
        results = [(p, check(p.read_text(encoding="utf-8"), words)) for p in args.files]
        for path, findings in results:
            for line, word in findings:
                print(f"{path}:{line}: design leakage: {word}")
        return int(any(findings for _, findings in results))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
