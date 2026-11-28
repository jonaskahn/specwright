#!/usr/bin/env python3
"""Analyse an existing project or feature: code roots, inventory, area evidence, gap table.

    analyze.py roots [--add PATH ...]          registered and detected code roots
    analyze.py inventory                       light inventory of every root and the docs
    analyze.py area <keyword> [<keyword> ...]  pointers to read for one area (code, tests, docs)
    analyze.py cite <root>/<path> --lines A[-B] a CODE citation for those lines
    analyze.py new <target> [--title T]        start 01-analysis/as-is/<target>.analysis.md
    analyze.py check <target|file>             validate the gap table; shape, asks, next step
    analyze.py new <FEAT-NNN> --verify         pre-ship check: one row per AC of that change
    analyze.py confirm <target>                after the user confirmed the asked rows

Common: --cwd <project> [--scope S] [--format text|json]. Code is read, never written.
Exit codes: 0 ok, 1 check findings, 2 usage or file error, 3 scope ambiguous.
"""

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(f"error: shared library missing at {_shared}/kitlib; reinstall this skill")
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import analysis, coderoots, discovery, fsio, inventory, paths, workspace  # noqa: E402

FOLDER = "01-analysis/as-is"


def _roots(root, scope) -> dict[str, Path]:
    return {r["name"]: Path(r["abs"]) for r in coderoots.registered(root, scope) if r["exists"]}


def _doc_folders(base: Path, roots: dict[str, Path]) -> list[tuple[Path, str]]:
    out = [(base / "00-inbox", "inbox")]
    for name, path in roots.items():
        # Root plans/README and non-Markdown docs use the same safe discovery boundary.
        out.extend((p, f"{name}/{p.relative_to(path).as_posix()}") for p in discovery._files(path))
    return out


def _verify_rows(base: Path, feat: str, text: str) -> str:
    """Pre-fill one Criteria row per AC of the change, Intended = that AC."""
    from kitlib import frontmatter, markdown

    story = paths.story(base, feat.split(":")[-1])
    if not story.is_file():
        raise ValueError(f"no story for {feat}")
    sp = frontmatter.parse(story.read_text(encoding="utf-8"))
    acs = markdown.ac_blocks(markdown.sections(sp.body).get("Acceptance criteria"))
    rows = [
        f"| {ac_id} | {block.title} | {ac_id} | <CODE cite or None> | <status> | <confidence> | |"
        for ac_id, block in acs.items()
    ]
    text = re.sub(r"^\| C-1 \|.*$", "\n".join(rows), text, count=1, flags=re.M)
    return text.replace("kind: analysis\n", f"kind: analysis\nverifies: {feat}\n", 1)


def _print(data, fmt):
    if fmt == "json" or not isinstance(data, str):
        print(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(data)


def cmd_area(base, roots, words, limit):
    stems = [w.lower().rstrip("s") for w in words if len(w) >= 3]
    if not stems:
        raise ValueError("give at least one keyword of 3+ letters")
    rx = re.compile("|".join(re.escape(s) for s in stems), re.I)
    hits = {"code": [], "tests": [], "docs": []}
    for name, root in roots.items():
        for path, rel in inventory._files(root):
            if not rx.search(rel):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                n = len(rx.findall(text))
                if n == 0:
                    continue
            else:
                n = 99
            kind = (
                "tests" if inventory.TEST_FILE.search(path.name) or "/test" in f"/{rel}" else "code"
            )
            hits[kind].append((n, f"{name}/{rel}"))
    for folder, label in _doc_folders(base, roots):
        for p in (
            [folder]
            if folder.is_file()
            else sorted(folder.rglob("*.md"))
            if folder.is_dir()
            else []
        ):
            if p.is_symlink() or p.stat().st_size > inventory.MAX_BYTES:
                continue
            if "raw" in p.relative_to(folder).parts[:-1]:
                continue  # original bytes; the snapshot beside them is the citable text
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = [i for i, line in enumerate(text.splitlines(), 1) if rx.search(line)]
            if lines:
                rel = p.relative_to(folder).as_posix() if p != folder else ""
                hits["docs"].append(
                    (
                        len(lines),
                        f"{label}{'/' + rel if rel else ''}:L{lines[0]}"
                        + (f" (+{len(lines) - 1})" if len(lines) > 1 else ""),
                    )
                )
    return {
        "keywords": stems,
        **{
            k: [p for _, p in sorted(v, key=lambda x: (-x[0], x[1]))[:limit]]
            for k, v in hits.items()
        },
        "read_order": "name matches first, then hit count; docs give intended, code/tests actual",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "command",
        choices=["discover", "roots", "inventory", "area", "cite", "new", "check", "confirm"],
    )
    parser.add_argument("args", nargs="*")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    parser.add_argument("--add", nargs="+")
    parser.add_argument("--lines")
    parser.add_argument("--title")
    parser.add_argument("--verify", action="store_true", help="new: verify a change before ship")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument(
        "--confirm-scan", action="store_true", help="discover: user approved this repository scan"
    )
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--snapshot", help="discover: fingerprint returned by the first batch")
    parser.add_argument(
        "--confirmed-by-owner",
        action="store_true",
        help="confirm: owner confirmed the displayed analysis",
    )
    parser.add_argument("--format", choices=["text", "json"], default="json")
    a = parser.parse_args(argv)
    try:
        cwd = Path(a.cwd).resolve()
        if a.command == "discover":
            result = discovery.discover(
                cwd,
                consent=a.confirm_scan,
                scope=a.scope,
                batch_size=a.batch_size,
                offset=a.offset,
                snapshot=a.snapshot,
            )
            _print(result, a.format)
            return 3 if result["state"] == "consent_required" else 0
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace; run sw-start first")
        scope = workspace.resolve(
            root, a.scope, None, cwd, a.command in ("roots", "inventory", "new")
        )
        base = workspace.scope_dir(root, scope)
        if a.command == "roots":
            if a.add:
                coderoots.register(root, scope, a.add)
            _print(
                {
                    "registered": coderoots.registered(root, scope),
                    "detected": coderoots.detect(root, scope),
                },
                a.format,
            )
            return 0
        roots = _roots(root, scope)
        if a.command == "inventory":
            code = {name: inventory.scan_code(path, name) for name, path in roots.items()}
            docs = inventory.scan_docs(_doc_folders(base, roots))
            inv = {
                "date": datetime.date.today().isoformat(),
                "roots": [r for r in coderoots.registered(root, scope) if r["exists"]],
                "code": code,
                "docs": docs,
                "candidates": inventory.candidates(code, docs),
            }
            fsio.atomic_write(
                base / ".metadata" / "inventory.json", json.dumps(inv, indent=1, ensure_ascii=False)
            )
            fsio.atomic_write(base / FOLDER / "inventory.md", inventory.render(inv))
            summary = {
                "written": [f"{FOLDER}/inventory.md", ".metadata/inventory.json"],
                "roots": [r["name"] for r in inv["roots"]],
                "candidates": [c["name"] for c in inv["candidates"][:15]],
                "detected_unregistered": [d["path"] for d in coderoots.detect(root, scope)],
            }
            _print(summary, a.format)
            return 0
        if a.command == "area":
            _print(cmd_area(base, roots, a.args, a.limit), a.format)
            return 0
        if a.command == "cite":
            if len(a.args) != 1 or not a.lines:
                raise ValueError("usage: cite <root>/<path> --lines A[-B]")
            start, _, end = a.lines.partition("-")
            print(analysis.cite(roots, a.args[0], int(start), int(end) if end else None))
            return 0
        if a.command == "new":
            if len(a.args) != 1 or not re.fullmatch(r"[A-Za-z0-9][\w.-]{1,60}", a.args[0]):
                raise ValueError("usage: new <target> (FEAT-NNN or a slug such as refund)")
            target = a.args[0]
            path = (
                base
                / FOLDER
                / (f"{target}.verify.analysis.md" if a.verify else f"{target}.analysis.md")
            )
            if path.exists():
                raise ValueError(f"{path.relative_to(base)} exists; edit it")
            tpl = (_here.parent / "assets" / "analysis.md").read_text(encoding="utf-8")
            text = (
                tpl.replace("<TARGET>", target)
                .replace("<SCOPE>", scope)
                .replace("<TITLE>", a.title or target)
                .replace("<DATE>", datetime.date.today().isoformat())
                .replace("<ROOTS>", ", ".join(sorted(roots)))
            )
            if a.verify:
                text = _verify_rows(base, target, text)
            fsio.atomic_write(path, text)
            print(path.relative_to(base).as_posix())
            return 0
        if a.command == "confirm":
            if not a.confirmed_by_owner:
                raise ValueError(
                    "show the analysis and ask the owner; "
                    "pass --confirmed-by-owner only after their confirmation"
                )
            if len(a.args) != 1:
                raise ValueError("usage: confirm <target>")
            path = base / FOLDER / f"{a.args[0]}.analysis.md"
            result = analysis.check(path, roots)
            if result["findings"]:
                raise ValueError("fix the table first: " + "; ".join(result["findings"][:3]))
            text = path.read_text(encoding="utf-8")
            text = re.sub(r"^status:.*$", "status: confirmed", text, count=1, flags=re.M)
            text = re.sub(r"^owner_confirmed_hash:.*\n?", "", text, count=1, flags=re.M)
            digest = analysis.confirmation_hash(text)
            text = text.replace(
                "status: confirmed\n", f"status: confirmed\nowner_confirmed_hash: {digest}\n", 1
            )
            fsio.atomic_write(path, text)
            print(json.dumps({"confirmed": a.args[0], "shape": result["shape"]}))
            return 0
        if a.command == "check":
            if len(a.args) != 1:
                raise ValueError("usage: check <target|file>")
            p = Path(a.args[0])
            path = (
                p
                if p.suffix == ".md" and p.is_file()
                else base / FOLDER / f"{a.args[0]}.analysis.md"
            )
            if not path.is_file():
                raise ValueError(f"no analysis file: {path}")
            result = analysis.check(path, roots)
            _print(result, a.format)
            return 0 if result["pass"] else 1
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 3
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
