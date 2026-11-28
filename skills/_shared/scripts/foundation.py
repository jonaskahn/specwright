#!/usr/bin/env python3
"""Foundation story for a new codebase: structure, format, lint, tests with coverage, one
`make check` gate, CI and an AI workflow file (AGENTS.md) for coding agents.

    foundation.py questions                      ≤ 5 questions, prefilled from the stack
    foundation.py set --decline                  the owner declined; sw-start stops offering it
    foundation.py set --defaults | [--layer L --build B --format F --lint X --test T]
                      [--coverage N] [--ci C] [--hooks H] [--ai-workflow W]
    foundation.py analyze                        what each code folder already has (names only)
    foundation.py draft --feat FEAT-NNN [--bo BO-NNN]
                                                 fill the reserved story; write reference files
                                                 features/FEAT-NNN/foundation/{Makefile,AGENTS.md}
                                                 and <layer>/AGENTS.md when there are several layers

Common: --cwd <project> [--scope S]. Tooling lives in stack.yaml `tooling` (outside the stack
lock hash). Exit codes: 0 ok, 2 usage or file error.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402

from kitlib import coderoots, foundation, frontmatter, fsio, paths, stack, workspace  # noqa: E402


def _profile_path(root, scope):
    return stack.path_for(root, scope)


def _splice(text: str, sections: dict[str, str]) -> str:
    """Replace each named top-level section body, keeping front matter and Identity."""
    for name, body in sections.items():
        pattern = re.compile(rf"(^## {re.escape(name)}\n)(.*?)(?=^## |\Z)", re.M | re.S)
        if not pattern.search(text):
            raise ValueError(f"story has no '## {name}' section")
        replacement = "\n" + body.strip() + "\n\n"
        text = pattern.sub(lambda m, rep=replacement: m.group(1) + rep, text, count=1)
    return text


def _set_fm(text: str, key: str, value: str) -> str:
    head, sep, body = text.partition("\n---\n")
    if re.search(rf"^{key}:.*$", head, re.M):
        head = re.sub(rf"^{key}:.*$", f"{key}: {value}", head, count=1, flags=re.M)
    else:
        head += f"\n{key}: {value}"
    return head + sep + body


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["questions", "set", "draft", "analyze"])
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--defaults", action="store_true")
    parser.add_argument(
        "--decline", action="store_true", help="the owner declined; never offer again"
    )
    parser.add_argument("--layer")
    for opt in ("build", "format", "lint", "test", "ci", "hooks", "ai-workflow"):
        parser.add_argument(f"--{opt}")
    parser.add_argument("--coverage", type=int)
    parser.add_argument("--feat")
    parser.add_argument("--bo")
    a = parser.parse_args(argv)
    try:
        cwd = Path(a.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, a.scope, a.feat, cwd, a.command != "questions")
        base = workspace.scope_dir(root, scope)
        profile = stack.effective(root, scope)
        if a.command == "questions":
            print(json.dumps({"questions": foundation.questions(profile)}, indent=2))
            return 0
        if a.command == "analyze":
            roots = coderoots.all_roots(root, scope) or [root.parent]
            report = {str(r): foundation.existing_setup(r) for r in roots}
            print(json.dumps({"existing": report}, indent=2))
            return 0
        path = _profile_path(root, scope)
        data = stack.load(path) or stack.empty()
        if a.command == "set":
            tooling = data.get("tooling") or foundation.default_tooling(profile)
            if a.defaults:
                tooling = foundation.default_tooling(profile)
            if a.decline:
                tooling = {"declined": True}
            if a.layer:
                entry = tooling.setdefault("layers", {}).setdefault(a.layer, {})
                lang = foundation.language_of(profile, a.layer)
                if lang:
                    entry.setdefault("language", lang)
                for key in ("build", "format", "lint", "test"):
                    if getattr(a, key):
                        entry[key] = getattr(a, key)
                cat = foundation.CATALOG.get(entry.get("language", ""), {})
                if entry.get("build") and entry["build"] not in cat.get("cmd", {}):
                    raise ValueError(
                        f"build {entry['build']} not known for {entry.get('language')}"
                    )
            if a.coverage is not None:
                if not 0 < a.coverage <= 100:
                    raise ValueError("--coverage must be 1-100")
                tooling["coverage"] = a.coverage
            for key, attr in (("ci", "ci"), ("hooks", "hooks"), ("ai_workflow", "ai_workflow")):
                if getattr(a, attr):
                    tooling[key] = getattr(a, attr)
            data["tooling"] = tooling
            stack.save(path, data)
            print(json.dumps({"saved": str(path.relative_to(root)), "tooling": tooling}, indent=2))
            return 0
        # draft
        if not a.feat:
            raise ValueError("draft needs --feat FEAT-NNN")
        feat = a.feat.split(":")[-1]
        story = paths.story(base, feat)
        if not story.is_file():
            raise ValueError(f"no story {feat}; reserve and create it first (new_story.py)")
        tooling = data.get("tooling")
        if not tooling:
            raise ValueError("no tooling yet: foundation.py set --defaults (or the answers)")
        text = story.read_text(encoding="utf-8")
        fm = frontmatter.parse(text).fm or {}
        bo = a.bo or next(iter(fm.get("bo") or []), None)
        if not bo:
            raise ValueError("name the business objective: --bo BO-NNN")
        sections = foundation.story_sections(tooling, bo, feat.split("-")[1])
        text = _splice(text, sections)
        text = _set_fm(text, "kind", "foundation")
        if not fm.get("bo"):
            text = _set_fm(text, "bo", f"[{bo}]")
        fsio.atomic_write(story, text)
        name = str(workspace.load(base / workspace.FLAT_MANIFEST).get("name") or scope)
        lines = {k: stack.layer_line(profile, k) for k in foundation.code_layers(profile)}
        out = paths.foundation_dir(base, feat)
        fsio.atomic_write(out / "Makefile", foundation.makefile(tooling, name))
        written = ["Makefile"]
        if tooling.get("ai_workflow", "none") != "none":
            fsio.atomic_write(
                out / "AGENTS.md",
                foundation.agents_md(
                    tooling, name, lines, ((profile or {}).get("locked") or {}).get("hash")
                ),
            )
            written.append("AGENTS.md")
            if len(tooling.get("layers") or {}) > 1:
                for layer in tooling["layers"]:
                    fsio.atomic_write(
                        out / layer / "AGENTS.md", foundation.layer_agents_md(tooling, layer)
                    )
                    written.append(f"{layer}/AGENTS.md")
        print(
            json.dumps(
                {
                    "story": paths.story(base, feat).relative_to(base).as_posix(),
                    "files": [(out / w).relative_to(base).as_posix() for w in written],
                },
                indent=2,
            )
        )
        return 0
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, workspace.WorkspaceError, stack.StackError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
