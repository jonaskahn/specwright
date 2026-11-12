#!/usr/bin/env python3
"""Check that each packaged skill is self-contained.

Unzips every ``<skill>.zip`` in a distribution folder (or reads built skill folders) and
fails when a skill

- names a ``references/``, ``scripts/`` or ``assets/`` file that the package does not carry, or
- has a script that cannot start (a missing shared library, a missing sibling module).

Scripts run with ``--help`` from an empty working folder, the way a host would start them.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "_shared" / "scripts"))

from kitlib import guard  # noqa: E402

REFERENCE = re.compile(
    r"(?<![\w./-])((?:\.\./)?(?:_shared/)?(?:references|scripts|assets)/"
    r"[\w./-]*[\w-]\.(?:md|py|html|json|css|svg|txt|jsonl))"
)
TEXT_SUFFIXES = {".md", ".py", ".json", ".html"}
PLACEHOLDERS = "{<*"


def dangling_references(skill: Path) -> list[str]:
    """``file -> reference`` lines for every named file the skill folder does not hold."""
    problems: list[str] = []
    for path in sorted(skill.rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for found in sorted(set(REFERENCE.findall(text))):
            rel = found.replace("../", "")
            if any(ch in rel for ch in PLACEHOLDERS):
                continue
            if not any(
                c.exists() for c in (skill / rel, skill / "_shared" / rel, path.parent / rel)
            ):
                problems.append(f"{path.relative_to(skill).as_posix()}: names missing {rel}")
    return problems


def broken_scripts(skill: Path) -> list[str]:
    """Scripts that exit non-zero on ``--help``; the last stderr line says why."""
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="specwright-verify-") as empty:
        for script in sorted(skill.glob("scripts/*.py")):
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True,
                text=True,
                cwd=empty,
                timeout=60,
            )
            if result.returncode != 0:
                reason = (result.stderr.strip().splitlines() or ["no error output"])[-1]
                problems.append(f"scripts/{script.name}: exit {result.returncode}: {reason[:160]}")
    return problems


def shared_problems(skill: Path) -> list[str]:
    """A packaged skill must hold a manifest that matches its shared files."""
    if not (skill / "_shared" / guard.MANIFEST).is_file():
        return [f"_shared/{guard.MANIFEST} is missing"]
    return guard.check(skill)


def verify_skill(skill: Path) -> list[str]:
    found = shared_problems(skill) + dangling_references(skill) + broken_scripts(skill)
    return [f"{skill.name}: {p}" for p in found]


def verify_zips(dist: Path) -> list[str]:
    archives = sorted(dist.glob("*.zip"))
    if not archives:
        return [f"{dist}: no skill zips found"]
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="specwright-unzip-") as raw:
        for archive in archives:
            target = Path(raw) / archive.stem
            target.mkdir()
            with zipfile.ZipFile(archive) as bundle:
                bundle.extractall(target)
            folder = target / archive.stem
            if not (folder / "SKILL.md").is_file():
                problems.append(f"{archive.name}: no {archive.stem}/SKILL.md at the top level")
                continue
            problems.extend(verify_skill(folder))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    args = parser.parse_args(argv)
    problems = verify_zips(args.dist)
    for line in problems:
        print(line, file=sys.stderr)
    print(f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
