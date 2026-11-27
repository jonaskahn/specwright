#!/usr/bin/env python3
"""Flag hedges, filler and unquantified words in agent-facing artifacts (agent-style.md).

    style_check.py <file>... [--format json] [--strict]

Front matter, fenced code, inline code and quoted UI text are skipped. Exit codes: 0 report
printed (warnings only), 1 findings under --strict, 2 usage or unreadable file.
"""

import argparse
import json
import re
import sys
from pathlib import Path

HEDGES = [
    "should probably",
    "probably",
    "might",
    "ideally",
    "as needed",
    "if possible",
    "as appropriate",
    "appropriate",
    "user-friendly",
    "etc.",
    "and so on",
    "various",
    "somehow",
    "maybe",
    "hopefully",
    "tbd",
    "to be decided",
]
FILLER = [
    "in order to",
    "it is important to note",
    "it should be noted",
    "basically",
    "please note",
    "simply",
    "just",
    "obviously",
    "of course",
]
VAGUE = [
    "fast",
    "slow",
    "large",
    "small",
    "many",
    "few",
    "soon",
    "recent",
    "secure",
    "scalable",
    "robust",
    "simple",
    "easy",
    "intuitive",
    "flexible",
    "reasonable",
    "optimal",
    "efficient",
    "quickly",
]
NUMBER = re.compile(r"\d")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”|`[^`]*`')
FENCE = re.compile(r"^\s*(```|~~~)")


def _patterns():
    out = []
    for kind, words in (("hedge", HEDGES), ("filler", FILLER), ("vague", VAGUE)):
        for w in words:
            out.append((kind, w, re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I)))
    return out


PATTERNS = _patterns()


def check_text(text: str, name: str) -> list[dict]:
    findings, fenced, front = [], False, False
    for number, line in enumerate(text.splitlines(), 1):
        if number == 1 and line.strip() == "---":
            front = True
            continue
        if front:
            front = line.strip() != "---"
            continue
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced or line.lstrip().startswith(("|---", "<!--")):
            continue
        plain = QUOTED.sub("", line)
        hits = []
        for kind, word, rx in PATTERNS:
            if rx.search(plain):
                if kind == "vague" and NUMBER.search(plain):
                    continue  # the line already carries a measure
                hits.append((kind, word))
        for kind, word in hits:
            if not any(word != other and word in other for _, other in hits):
                findings.append({"file": name, "line": number, "kind": kind, "word": word})
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    findings = []
    try:
        for f in args.files:
            p = Path(f)
            if p.is_file():
                findings += check_text(p.read_text(encoding="utf-8"), f)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps({"findings": findings, "count": len(findings)}, indent=2))
    else:
        for x in findings:
            print(f"{x['file']}:{x['line']}: {x['kind']} '{x['word']}'")
        print(f"style: {len(findings)} warning(s)")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    sys.exit(main())
