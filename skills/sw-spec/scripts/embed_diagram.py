#!/usr/bin/env python3
"""Show a rendered diagram inside its story: a Visuals line and an image line under UI/UX.

The picture is `diagrams/FEAT-NNN.<type>.svg`, drawn from the JSON beside it, and that JSON must
cite this feature or one of its criteria. The image line is written relative to the story file,
so a Markdown viewer, an editor and the console all draw it. The draft hash is restamped.

Exit codes: 0 written, 1 invalid input, 2 usage or file error, 3 refused because the story is
approved (embedding changes its hash; raise a change request instead).
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
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from check_offline import check_text  # noqa: E402

from kitlib import frontmatter, fsio, hashing, ids, illustration  # noqa: E402
from kitlib.borders import find_one_sided  # noqa: E402

EDITABLE = {"draft", "in-review"}
_HEADING = re.compile(r"^## ")
_BULLET = re.compile(r"^\s*[-*]\s")


class Refused(ValueError):
    """The story is approved, so the picture is drawn but not embedded."""


def _svg(base: Path, name: str) -> Path:
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts or rel.parts[:1] != ("diagrams",):
        raise ValueError("the picture must be a path inside diagrams/, such as diagrams/x.svg")
    if rel.suffix != ".svg" or len(rel.parts) != 2:
        raise ValueError("embed an .svg file; render one with render_diagram.py spec.json out.svg")
    path = base / rel
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{name} does not exist")
    return path


def _alt(text: str) -> str:
    alt = " ".join(text.replace("[", "(").replace("]", ")").split())
    if not alt:
        raise ValueError("--alt is required: say what the picture shows and cite its criteria")
    return alt


def _section(lines: list[str]) -> tuple[int, int]:
    start = next((i for i, line in enumerate(lines) if line.strip() == "## UI/UX"), None)
    if start is None:
        raise ValueError("the story has no ## UI/UX section")
    end = next((i for i in range(start + 1, len(lines)) if _HEADING.match(lines[i])), len(lines))
    return start, end


def embed(text: str, name: str, alt: str) -> str:
    """The story with the picture listed and embedded once, wherever it was before."""
    lines = text.split("\n")
    start, end = _section(lines)
    file = Path(name).name
    body = [
        line
        for line in lines[start + 1 : end]
        if not (name in line or (line.lstrip().startswith("![") and f"diagrams/{file}" in line))
    ]
    first = next((i for i, line in enumerate(body) if line.startswith("Visuals:")), None)
    gap = 0
    if first is None:
        while body and not body[-1].strip():
            body.pop()
            gap += 1
        body += ["", "Visuals:"]
        first = len(body) - 1
    elif re.match(r"Visuals:\s*None\b", body[first]):
        body[first] = "Visuals:"
    last = first
    while last + 1 < len(body) and (
        _BULLET.match(body[last + 1]) or body[last + 1].lstrip().startswith("![")
    ):
        last += 1
    bullets = [i for i in range(first + 1, last + 1) if _BULLET.match(body[i])]
    at = bullets[-1] + 1 if bullets else first + 1
    body.insert(at, f"- diagram — {alt} — {name}")
    after = at + 1
    while after < len(body) and body[after].lstrip().startswith("!["):
        after += 1
    body.insert(after, f"![{alt}](../{name})")
    body += [""] * gap
    return "\n".join([*lines[: start + 1], *body, *lines[end:]])


def run(base: Path, feature: str, name: str, alt: str, scope: str | None = None) -> str:
    if not ids.matches_type("feature", feature):
        raise ValueError(f"{feature} is not a feature ID such as FEAT-002")
    story = base / "02-drafts" / f"{feature}.story.md"
    if not story.is_file():
        raise ValueError(f"{story} does not exist")
    text = story.read_text(encoding="utf-8")
    parsed = frontmatter.parse(text)
    if parsed.error or not parsed.fm:
        raise ValueError(parsed.error or "story requires front matter")
    status = str(parsed.fm.get("status") or "")
    if status not in EDITABLE:
        raise Refused(
            f"{feature} is {status}: embedding changes its draft hash, so raise a change request "
            "and amend it through sw-spec; the picture stays drawn"
        )
    path = _svg(base, name)
    chosen = scope or str(parsed.fm.get("scope") or "")
    number = ids.feat_number(feature)
    found, _ = illustration.pictures(text, base, chosen, feature, number)
    if name not in {row["svg"] for row in found}:
        raise ValueError(
            f"{name} needs a JSON spec of the same name that cites {feature} or one of its criteria"
        )
    flaws = [f"line {n}: offline forbids {token}" for n, token in check_text(path.read_text())]
    flaws += [f"line {n}: {message}" for n, message in find_one_sided(path.read_text())]
    if flaws:
        raise ValueError(f"{name} fails its checks: " + "; ".join(flaws))
    updated = hashing.stamp(embed(text, name, _alt(alt)))
    if updated != text:
        fsio.atomic_write(story, updated)
    return str(story)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature", help="feature ID such as FEAT-002")
    parser.add_argument("picture", help="project-relative path, such as diagrams/FEAT-002.flow.svg")
    parser.add_argument("--alt", required=True, help="one sentence, with the criteria it shows")
    parser.add_argument("--scope-root", required=True, type=Path, help="resolved project folder")
    parser.add_argument("--scope", help="project scope when the story front matter has none")
    args = parser.parse_args(argv)
    try:
        target = run(args.scope_root, args.feature, args.picture, args.alt, args.scope)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(target)
    print(f"next: card_gen.py {target}, then sw_lint.py --gate review", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
