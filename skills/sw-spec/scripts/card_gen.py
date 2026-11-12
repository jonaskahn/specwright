#!/usr/bin/env python3
"""Create a deterministic story index without acceptance-criterion text.

Exit codes: 0 generated, 1 invalid content, 2 usage or file error.
Default output is the sibling .card.md; --stdout leaves files unchanged.
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

from kitlib import frontmatter, fsio, ids, markdown, schema  # noqa: E402


def validate_card(text: str) -> None:
    fm, body = frontmatter.split(text)
    sections = markdown.sections(body)
    if not fm or fm.get("card") is not True or fm.get("home") != "jira":
        raise ValueError("card requires card: true and home: jira")
    if len(text.splitlines()) > 80 or list(sections) != ["Summary", "Links", "Trace"]:
        raise ValueError("card requires at most 80 lines and Summary, Links, Trace in order")
    if not sections["Summary"].text or len(sections["Summary"].text.split()) > 150:
        raise ValueError("Summary requires 1..150 words")
    if re.search(r"\bAC-\d{3}-\d+\b|^\s*(Given|When|Then)\b", body, re.M):
        raise ValueError("card must not duplicate acceptance criteria")


def generate(text: str) -> str:
    fm, body = frontmatter.split(text)
    if not fm or not ids.matches_type("feature", str(fm.get("id", ""))):
        raise ValueError("story requires a FEAT-NNN id")
    if not ids.is_scope(str(fm.get("scope", ""))):
        raise ValueError("story requires a scope of 2..5 uppercase letters")
    sections = markdown.iter_sections(body)
    if [s.name for s in sections] != schema.STORY_SECTIONS:
        raise ValueError("story requires twelve sections in canonical order")
    sec = {s.name: s for s in sections}
    goal = " ".join(sec["Goal"].text.split())
    if not goal or "<" in goal:
        raise ValueError("Goal is empty or has placeholders")
    goal = re.split(r"(?<=[.!?])\s+", goal, maxsplit=1)[0]
    numbers = []
    for line in sec["Business rules"].text.splitlines():
        match = re.match(r"\s*-\s+(BR-\d{3})\b(.*)", line)
        if match:
            values = re.findall(r"(?<![\w-])\d[\d,]*(?:\.\d+)?(?:[–-]\d+)?%?", match[2])
            numbers.append(match[1] + (": " + ", ".join(values) if values else ""))
    rules = ("Key rule numbers: " + "; ".join(numbers) + ".") if numbers else ""
    if len(rules.split()) >= 150:
        raise ValueError("rule numbers exceed the word budget; split the feature")
    summary = " ".join(goal.split()[: 150 - len(rules.split())])
    summary += (" " + rules) if rules else ""
    card_fm = {
        key: fm[key]
        for key in (
            "id",
            "type",
            "scope",
            "status",
            "links",
            "linked_version",
            "bo",
            "br",
            "nfr",
            "sources",
        )
        if key in fm
    }
    card_fm.update({"type": "feature", "card": True, "home": "jira"})
    trace_text = "\n".join(
        sec[name].text
        for name in ("Goal", "Business rules", "Non-functional", "Open questions", "Identity")
    )
    refs = [
        ref.qualified
        for ref in ids.find_refs(trace_text)
        if ids.prefix_of(ref.id) in {"BO", "BR", "NFR", "Q", "DEC", "CR"}
    ]
    links = fm.get("links") or []
    if not isinstance(links, list) or not all(isinstance(x, str) for x in links):
        raise ValueError("links must be a list of strings")
    home = ", ".join(links) or "Not published"
    if "\n" in home or "\r" in home:
        raise ValueError("links must be single-line values")
    output = frontmatter.render(
        card_fm,
        f"## Summary\n{summary}\n\n## Links\n"
        f"- Home: {home}\n- Draft: 02-drafts/{fm['id']}.story.md\n\n## "
        "Trace\n" + (" · ".join(dict.fromkeys(refs)) or "None") + "\n",
    )
    validate_card(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", type=Path)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not args.story.name.endswith(".story.md"):
            raise ValueError("input filename must end in .story.md")
        result = generate(args.story.read_text(encoding="utf-8"))
        if args.stdout:
            print(result, end="")
        else:
            target = args.story.with_name(args.story.name.replace(".story.md", ".card.md"))
            fsio.atomic_write(target, result)
            print(target)
        return 0
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
