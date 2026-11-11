#!/usr/bin/env python3
"""Map each public skill to the exact ``skills/_shared`` files it ships.

``skills/_shared/bundle-map.json`` is the source of truth for packaging:

- ``limits``       the per-skill file budget (the upload cap is a count, not a size).
- ``capabilities`` named shared capabilities and the root files each one adds.
- ``skills``       per skill, the capabilities it uses and the explicit ``shared`` list.

A skill's ``shared`` list is derived, never hand-edited: the roots are the shared files
its own text names (``_shared/...`` paths), the roots of its capabilities and, for every
Python root, the ``kitlib`` modules its code imports (followed through the AST,
including imports inside functions). ``--check`` fails when a stored list drifts from
that derivation or a skill exceeds its file budget; ``--write`` regenerates the lists.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SKILL_PREFIX = "sw-"
SHARED = "_shared"
MAP_NAME = "bundle-map.json"
KITLIB = Path("scripts/kitlib")
PROFILES = ("core", "extended")
JUNK_PARTS = {"__pycache__", ".DS_Store"}
SHARED_REF = re.compile(r"(?<![\w.-])(?:\.\./)?_shared/((?:references|scripts)/[\w./-]+\.\w+)")


class BundleError(ValueError):
    """The bundle map or a skill violates the packaging contract."""


def shared_folder(root: Path) -> Path:
    path = root / "skills" / SHARED
    if not path.is_dir():
        raise BundleError("skills/_shared is missing")
    return path


def map_path(root: Path) -> Path:
    return shared_folder(root) / MAP_NAME


def load_map(root: Path) -> dict:
    path = map_path(root)
    if not path.is_file():
        raise BundleError(f"skills/_shared/{MAP_NAME} is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"skills/_shared/{MAP_NAME} is unreadable: {exc}") from exc
    for key in ("limits", "capabilities", "skills"):
        if not isinstance(data.get(key), dict):
            raise BundleError(f"skills/_shared/{MAP_NAME} needs a '{key}' object")
    return data


def skill_folders(root: Path) -> list[Path]:
    skills = root / "skills"
    return sorted(
        p
        for p in skills.iterdir()
        if p.is_dir() and p.name.startswith(SKILL_PREFIX) and (p / "SKILL.md").is_file()
    )


def is_junk(path: Path) -> bool:
    return bool(JUNK_PARTS & set(path.parts)) or path.suffix == ".pyc"


def type_files(kind: str) -> list[str]:
    """Skill-relative files that make up one diagram type, by convention."""
    return [
        f"assets/{kind}.html",
        f"references/type-{kind}.md",
        f"scripts/draw_types/{kind.replace('-', '_')}.py",
    ]


def extended_types(data: dict, skill_name: str) -> list[str]:
    """Types a skill ships only in the extended profile."""
    entry = data["skills"].get(skill_name, {})
    return list(entry.get("tiers", {}).get("extended", []))


def excluded_files(data: dict, skill_name: str, profile: str) -> set[str]:
    """Skill-relative files the profile leaves out; the extended profile leaves out none."""
    if profile not in PROFILES:
        raise BundleError(f"unknown profile '{profile}'; choose one of {', '.join(PROFILES)}")
    if profile == "extended":
        return set()
    return {rel for kind in extended_types(data, skill_name) for rel in type_files(kind)}


def own_files(skill: Path, skip: frozenset[str] | set[str] = frozenset()) -> list[Path]:
    """Files a skill ships by itself, matching what packaging copies."""
    return sorted(
        p
        for p in skill.rglob("*")
        if p.is_file()
        and not is_junk(p.relative_to(skill))
        and SHARED not in p.relative_to(skill).parts[:1]
        and p.relative_to(skill).as_posix() not in skip
    )


def imported_modules(path: Path, kitlib_dir: Path) -> set[str]:
    """kitlib modules a Python file imports, including imports inside functions."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module == "kitlib":
            found.update(a.name for a in node.names if (kitlib_dir / f"{a.name}.py").is_file())
        elif node.module.startswith("kitlib."):
            found.add(node.module.split(".")[1])
    return {m for m in found if (kitlib_dir / f"{m}.py").is_file()}


def python_closure(shared: Path, roots: set[str]) -> set[str]:
    """Roots plus every kitlib module reachable from the Python roots."""
    kitlib_dir = shared / KITLIB
    needed = set(roots)
    pending = [r for r in roots if r.endswith(".py")]
    scanned: set[str] = set()
    while pending:
        rel = pending.pop()
        if rel in scanned:
            continue
        scanned.add(rel)
        path = shared / rel
        if not path.is_file():
            continue
        modules = imported_modules(path, kitlib_dir)
        if modules:
            needed.add((KITLIB / "__init__.py").as_posix())
        for module in modules:
            dep = (KITLIB / f"{module}.py").as_posix()
            needed.add(dep)
            pending.append(dep)
    return needed


def own_roots(skill: Path) -> tuple[set[str], list[str]]:
    """Shared files a skill names in its text or imports from its own code."""
    shared = skill.parent / SHARED
    roots: set[str] = set()
    problems: list[str] = []
    kitlib_dir = shared / KITLIB
    for path in own_files(skill):
        if path.suffix == ".py":
            for module in imported_modules(path, kitlib_dir):
                roots.add((KITLIB / f"{module}.py").as_posix())
        if path.suffix not in {".md", ".py"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for ref in SHARED_REF.findall(text):
            if (shared / ref).is_file():
                roots.add(ref)
            elif path.suffix == ".md":
                problems.append(f"{skill.name}: {path.relative_to(skill)} names missing {ref}")
    return roots, problems


def derive(root: Path, data: dict, skill: Path) -> tuple[list[str], list[str]]:
    """The sorted shared list a skill must ship, plus problems met while deriving it."""
    shared = shared_folder(root)
    entry = data["skills"].get(skill.name, {})
    roots, problems = own_roots(skill)
    for name in entry.get("capabilities", []):
        capability = data["capabilities"].get(name)
        if capability is None:
            problems.append(f"{skill.name}: unknown capability '{name}'")
            continue
        for rel in capability.get("roots", []):
            if (shared / rel).is_file():
                roots.add(rel)
            else:
                problems.append(f"capability '{name}': root {rel} does not exist")
    return sorted(python_closure(shared, roots)), problems


def count_files(root: Path, data: dict, skill: Path, profile: str = "extended") -> int:
    skip = excluded_files(data, skill.name, profile)
    return len(own_files(skill, skip)) + len(data["skills"].get(skill.name, {}).get("shared", []))


def shared_list(root: Path, skill_name: str) -> list[str]:
    """The stored shared list for packaging; fail closed when the map has no entry."""
    data = load_map(root)
    entry = data["skills"].get(skill_name)
    if entry is None:
        raise BundleError(f"{skill_name} has no entry in skills/_shared/{MAP_NAME}")
    shared = shared_folder(root)
    missing = [rel for rel in entry.get("shared", []) if not (shared / rel).is_file()]
    if missing:
        raise BundleError(f"{skill_name}: mapped shared files are missing: {', '.join(missing)}")
    return list(entry.get("shared", []))


def budget_error(root: Path, skill: Path, profile: str = "extended") -> str | None:
    """A message when packaging the skill would exceed the file cap, else None."""
    data = load_map(root)
    cap = int(data["limits"].get("max_files", 200))
    total = count_files(root, data, skill, profile)
    if total > cap:
        return f"{skill.name} would ship {total} files in the {profile} profile; the cap is {cap}"
    return None


def check(root: Path) -> tuple[list[str], list[str]]:
    """Return (problems, warnings)."""
    try:
        data = load_map(root)
        shared = shared_folder(root)
    except BundleError as exc:
        return [str(exc)], []
    problems: list[str] = []
    warnings: list[str] = []
    limits = data["limits"]
    cap = int(limits.get("max_files", 200))
    target = int(limits.get("target_files", cap))
    skills = skill_folders(root)
    names = {s.name for s in skills}
    for name in sorted(set(data["skills"]) - names):
        problems.append(f"{name}: in the map but not a public skill")
    for skill in skills:
        if skill.name not in data["skills"]:
            problems.append(f"{skill.name}: has no entry in {MAP_NAME}")
            continue
        wanted, found = derive(root, data, skill)
        problems.extend(found)
        stored = data["skills"][skill.name].get("shared", [])
        for rel in sorted(set(wanted) - set(stored)):
            problems.append(f"{skill.name}: needs {rel} but the map omits it")
        for rel in sorted(set(stored) - set(wanted)):
            problems.append(f"{skill.name}: ships {rel} but nothing needs it")
        if stored != sorted(set(stored)):
            problems.append(f"{skill.name}: shared list must be sorted and unique")
        for rel in stored:
            if not (shared / rel).is_file():
                problems.append(f"{skill.name}: mapped file {rel} does not exist")
        kinds = extended_types(data, skill.name)
        if len(kinds) != len(set(kinds)):
            problems.append(f"{skill.name}: tiers.extended lists a type twice")
        for kind in kinds:
            for rel in type_files(kind):
                # Legacy types render from shared code, so their own module is optional.
                if not rel.startswith("scripts/") and not (skill / rel).is_file():
                    problems.append(f"{skill.name}: extended type '{kind}' lacks {rel}")
        for profile in PROFILES if kinds else ("extended",):
            total = count_files(root, data, skill, profile)
            if total > cap:
                problems.append(
                    f"{skill.name}: {total} files exceed the cap of {cap} ({profile} profile)"
                )
            elif total > target:
                warnings.append(
                    f"{skill.name}: {total} files is above the target of {target} ({profile})"
                )
    return problems, warnings


def write(root: Path) -> list[str]:
    """Regenerate each skill's shared list; return the skills that changed."""
    data = load_map(root)
    changed: list[str] = []
    for skill in skill_folders(root):
        entry = data["skills"].setdefault(skill.name, {"capabilities": ["core"], "shared": []})
        wanted, problems = derive(root, data, skill)
        if problems:
            raise BundleError("; ".join(problems))
        if entry.get("shared") != wanted:
            entry["shared"] = wanted
            changed.append(skill.name)
    if changed:
        map_path(root).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def report(root: Path) -> str:
    data = load_map(root)
    shared = shared_folder(root)
    cap = int(data["limits"].get("max_files", 200))
    rows = [f"{'skill':<22}{'own':>5}{'shared':>8}{'files':>7}{'KB':>7}  capabilities"]
    shipped: set[str] = set()
    for skill in skill_folders(root):
        entry = data["skills"].get(skill.name, {})
        stored = entry.get("shared", [])
        shipped.update(stored)
        tiered = bool(extended_types(data, skill.name))
        for profile in PROFILES if tiered else ("extended",):
            files = own_files(skill, excluded_files(data, skill.name, profile))
            size = sum(p.stat().st_size for p in files)
            size += sum((shared / rel).stat().st_size for rel in stored if (shared / rel).is_file())
            label = f"{skill.name} ({profile})" if tiered else skill.name
            rows.append(
                f"{label:<22}{len(files):>5}{len(stored):>8}{len(files) + len(stored):>7}"
                f"{size // 1024:>7}  {', '.join(entry.get('capabilities', []))}"
            )
    rows.append(f"\nfile cap: {cap} per skill")
    unshipped = sorted(
        p.relative_to(shared).as_posix()
        for p in shared.rglob("*")
        if p.is_file() and not is_junk(p.relative_to(shared)) and p.name != MAP_NAME
    )
    unshipped = [rel for rel in unshipped if rel not in shipped]
    if unshipped:
        rows.append("shipped by no skill: " + ", ".join(unshipped))
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="verify the map and file budget")
    group.add_argument("--write", action="store_true", help="regenerate the shared lists")
    group.add_argument("--report", action="store_true", help="show files and size per skill")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.write:
            for name in write(root):
                print(f"updated {name}")
            return 0
        if args.report:
            print(report(root))
            return 0
        problems, warnings = check(root)
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        for problem in problems:
            print(problem, file=sys.stderr)
        if problems:
            print("run `make format bundle` to regenerate the shared lists", file=sys.stderr)
        return 1 if problems else 0
    except (OSError, BundleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
