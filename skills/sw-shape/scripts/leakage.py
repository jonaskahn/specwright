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

from kitlib import frontmatter, markdown  # noqa: E402

DEFAULT_WORDS = _here.parent / "references" / "leakage-words.md"


def load_words(path: Path = DEFAULT_WORDS) -> list[str]:
    words = [
        line[2:].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("- ")
    ]
    if not words or any(not word for word in words):
        raise ValueError("word list requires nonempty '- phrase' entries")
    return words


CORE = {"problem", "outcome", "smallest valuable outcome"}


def check(text: str, words: list[str], also: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    return scan(text, words, also)[0]


def scan(
    text: str, words: list[str], also: tuple[str, ...] = ()
) -> tuple[list[tuple[int, str]], list[str], list[str]]:
    """Findings, the sections scanned and the sections left unscanned."""
    parsed = frontmatter.parse(text)
    if parsed.error:
        raise ValueError(parsed.error)
    sections = list(markdown.iter_sections(parsed.body, first_line=parsed.body_line))
    extra = {name.casefold() for name in also}
    core = [s for s in sections if s.name.casefold() in CORE]
    if len(core) != 2 or sum(s.name.casefold() == "problem" for s in core) != 1:
        raise ValueError("expected one Problem and one Smallest valuable outcome section")
    selected = [s for s in sections if s.name.casefold() in CORE | extra]
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
    scanned = [s.name for s in selected]
    skipped = [s.name for s in sections if s not in selected]
    return sorted(set(findings)), scanned, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--words", type=Path, default=DEFAULT_WORDS)
    parser.add_argument(
        "--also", action="append", default=[], metavar="SECTION", help="scan this section too"
    )
    args = parser.parse_args(argv)
    try:
        words = load_words(args.words)
        results = [
            (p, *scan(p.read_text(encoding="utf-8"), words, tuple(args.also))) for p in args.files
        ]
        for path, findings, scanned, skipped in results:
            for line, word in findings:
                print(f"{path}:{line}: design leakage: {word}")
            print(f"{path}: scanned {', '.join(scanned)}")
            if skipped:
                print(f"{path}: not scanned {', '.join(skipped)}")
        print("A clean scan is not proof that no design leaked; read the sections above too.")
        return int(any(findings for _, findings, _, _ in results))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
