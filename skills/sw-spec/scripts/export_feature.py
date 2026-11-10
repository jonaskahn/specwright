#!/usr/bin/env python3
"""Write a derived Gherkin .feature file from a story's acceptance criteria.

The story stays the source of truth. The file records the story hash it came from and a hash of
its own body, so a hand-edited export is never overwritten. Exit codes: 0 generated,
1 content invalid or hand-edited file, 2 invocation or file error.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import re

from kitlib import frontmatter, hashing, ids, markdown  # noqa: E402

STEP = re.compile(r"^\s*(Given|When|Then|And|But)\b\s*(.*)$")


def render(text, name):
    parsed = frontmatter.parse(text)
    if parsed.error or not parsed.fm:
        raise ValueError(parsed.error or "story has no front matter")
    title = parsed.fm.get("title") or parsed.fm.get("jira_summary") or name
    section = markdown.sections(parsed.body).get("Acceptance criteria")
    blocks = markdown.ac_blocks(section)
    if not blocks:
        raise ValueError("story has no acceptance criteria to export")
    out = [f"Feature: {' '.join(str(title).split())}", ""]
    for ac_id, block in blocks.items():
        steps = [m.groups() for m in map(STEP.match, block.text.splitlines()) if m]
        kinds = [k for k, _ in steps]
        if not ({"Given", "When", "Then"} <= set(kinds)):
            raise ValueError(f"{ac_id} needs Given, When and Then to export")
        rules = sorted({r.id for r in ids.find_refs(block.text) if r.id.startswith("BR-")})
        tags = " ".join(f"@{t}" for t in [ac_id, *rules])
        out += [f"  {tags}", f"  Scenario: {ac_id} — {block.title or ac_id}"]
        out += [f"    {kind} {rest}".rstrip() for kind, rest in steps]
        out.append("")
    return "\n".join(out).rstrip() + "\n", hashing.draft_hash(text)


def with_header(body, source_hash):
    own = hashing.text_hash(body)
    return (
        "# generated; edit the story, not this file\n"
        f"# source-hash: {source_hash}\n"
        f"# content-hash: {own}\n" + body
    )


def hand_edited(existing):
    match = re.search(r"^# content-hash: (sha256:[0-9a-f]+)$", existing, re.M)
    if not match:
        return True
    body = "\n".join(line for line in existing.splitlines() if not line.startswith("# "))
    first = existing.split("\n", 3)
    body = first[3] if len(first) > 3 else ""
    return hashing.text_hash(body) != match.group(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("story", type=Path, help="path to FEAT-NNN.story.md")
    parser.add_argument("--stdout", action="store_true", help="preview without writing")
    args = parser.parse_args(argv)
    try:
        text = args.story.read_text(encoding="utf-8")
        name = args.story.name.split(".")[0]
        body, source_hash = render(text, name)
        output = with_header(body, source_hash)
        if args.stdout:
            print(output, end="")
            return 0
        target = args.story.with_name(f"{name}.feature")
        existing = target.read_text(encoding="utf-8") if target.exists() else ""
        if existing and existing != output and hand_edited(existing):
            print(f"error: {target.name} was edited by hand; not overwritten", file=sys.stderr)
            return 1
        target.write_text(output, encoding="utf-8")
        print(target)
        return 0
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
