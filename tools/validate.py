#!/usr/bin/env python3
"""Validate every skill folder against the Agent Skills rules plus the kit's own rules.

Exit codes: 0 clean, 1 findings with errors, 2 usage error. Warnings never fail the run.
Output lines look like 'path:line: CODE message' so they can be grepped.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from kitlib import frontmatter, miniyaml  # noqa: E402

PREFIX = "sw-"
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME, MAX_DESCRIPTION, DESCRIPTION_BUDGET, MAX_COMPAT = 64, 1024, 900, 500
MAX_BODY_LINES, WARN_BODY_LINES, MAX_BODY_TOKENS = 500, 400, 5000
MIN_TRIGGER_ROWS = 8
SPDX_LICENSES = {"MIT", "Apache-2.0", "BSD-3-Clause", "ISC"}
PATH_REF = re.compile(r"\b((?:references|scripts|assets)/[\w./-]+\.\w+)")


@dataclass
class Finding:
    path: str
    line: int
    code: str
    message: str
    error: bool = True

    def __str__(self) -> str:
        level = "" if self.error else " (warning)"
        return f"{self.path}:{self.line}: {self.code}{level} {self.message}"


class Report:
    def __init__(self, base: Path) -> None:
        self.base = base
        self.items: list[Finding] = []

    def add(self, path: Path, line: int, code: str, message: str, error: bool = True) -> None:
        try:
            shown = str(path.relative_to(self.base))
        except ValueError:
            shown = str(path)
        self.items.append(Finding(shown, line, code, message, error))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.items if f.error]


def _check_front_matter(skill: Path, parsed: frontmatter.Parsed, report: Report) -> None:
    md = skill / "SKILL.md"
    if parsed.error or parsed.fm is None:
        report.add(md, 1, "V001", parsed.error or "missing front matter")
        return
    fm = parsed.fm
    for key in fm:
        if key not in ALLOWED_KEYS:
            report.add(md, 1, "V002", f"front matter key '{key}' is outside the portable set")
    name = fm.get("name")
    if not isinstance(name, str) or not name:
        report.add(md, 1, "V003", "name is required")
    else:
        if len(name) > MAX_NAME or not NAME_RE.match(name):
            report.add(md, 1, "V004", "name must be lowercase letters, digits and single hyphens")
        if name != skill.name:
            report.add(md, 1, "V005", f"name '{name}' must match the folder '{skill.name}'")
        if not name.startswith(PREFIX):
            report.add(md, 1, "V006", f"name must start with '{PREFIX}'")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        report.add(md, 1, "V007", "description is required and must be a single-line string")
        return
    if len(desc) > MAX_DESCRIPTION:
        report.add(
            md, 1, "V008", f"description is {len(desc)} chars; the limit is {MAX_DESCRIPTION}"
        )
    elif len(desc) > DESCRIPTION_BUDGET:
        report.add(
            md, 1, "V009", f"description is {len(desc)} chars; aim for {DESCRIPTION_BUDGET}", False
        )
    if "Use when" not in desc and "Use only when" not in desc:
        report.add(md, 1, "V010", "description should say when to use the skill ('Use when ...')")
    if "Do NOT use" not in desc:
        report.add(md, 1, "V011", "description should end with 'Do NOT use for ... (use sw-x)'")
    if re.search(r"\b(I|you|your)\b", desc):
        report.add(md, 1, "V012", "write the description in third person", False)
    compat = fm.get("compatibility")
    if compat is not None and (not isinstance(compat, str) or len(compat) > MAX_COMPAT):
        report.add(md, 1, "V013", f"compatibility must be a string of at most {MAX_COMPAT} chars")
    meta = fm.get("metadata")
    if meta is not None and (
        not isinstance(meta, dict) or not all(isinstance(v, str) for v in meta.values())
    ):
        report.add(md, 1, "V014", "metadata must be a map of string values (quote versions)")
    lic = fm.get("license")
    if lic is not None and lic not in SPDX_LICENSES:
        report.add(md, 1, "V015", f"license should be an SPDX id such as MIT, got '{lic}'")


def _check_body(skill: Path, parsed: frontmatter.Parsed, report: Report) -> None:
    md = skill / "SKILL.md"
    lines = parsed.body.count("\n") + 1
    if lines > MAX_BODY_LINES:
        report.add(md, 1, "V020", f"body has {lines} lines; the limit is {MAX_BODY_LINES}")
    elif lines > WARN_BODY_LINES:
        report.add(
            md, 1, "V021", f"body has {lines} lines; consider moving detail to references", False
        )
    if len(parsed.body) // 4 > MAX_BODY_TOKENS:
        report.add(
            md,
            1,
            "V022",
            f"body is about {len(parsed.body) // 4} tokens; the limit is {MAX_BODY_TOKENS}",
        )
    for marker in ("Triggers", "Functional test"):
        if re.search(rf"^\W*{marker}\b", parsed.body, re.M):
            report.add(md, 1, "V023", f"'{marker}' belongs in evals/, not in the skill body")
    referenced = set(PATH_REF.findall(parsed.body))
    for ref in sorted(referenced):
        if not (skill / ref).exists():
            report.add(md, 1, "V024", f"referenced file '{ref}' does not exist")
    for sub in ("references", "scripts"):
        folder = skill / sub
        if not folder.is_dir():
            continue
        for item in sorted(folder.iterdir()):
            if item.name == "kitlib" or item.name.startswith(("_", ".")) or item.is_dir():
                continue
            if f"{sub}/{item.name}" not in referenced:
                report.add(
                    item, 1, "V025", f"'{sub}/{item.name}' is never mentioned in SKILL.md", False
                )
    for forbidden in ("README.md", "CHANGELOG.md", "INSTALL.md"):
        if (skill / forbidden).exists():
            report.add(
                skill / forbidden, 1, "V026", "skill folders carry no extra documentation files"
            )


def _stdlib_only(tree: ast.AST) -> list[str]:
    bad = []
    stdlib = set(sys.stdlib_module_names)
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name.split(".")[0] for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module.split(".")[0]]
        bad += [n for n in names if n not in stdlib and n != "kitlib"]
    return bad


def _check_scripts(skill: Path, report: Report) -> None:
    folder = skill / "scripts"
    if not folder.is_dir():
        return
    for script in sorted(folder.glob("*.py")):
        source = script.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, str(script))
        except SyntaxError as exc:
            report.add(script, exc.lineno or 1, "V030", f"syntax error: {exc.msg}")
            continue
        for module in sorted(set(_stdlib_only(tree))):
            report.add(
                script, 1, "V031", f"imports '{module}', which is not in the standard library"
            )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "input":
                report.add(script, node.lineno, "V032", "scripts must not prompt for input")
        if "argparse" not in source and "--help" not in source:
            report.add(
                script, 1, "V033", "script should be documented through argparse --help", False
            )


def _check_evals(skill: Path, evals: Path, report: Report) -> None:
    triggers = evals / skill.name / "triggers.jsonl"
    if not triggers.is_file():
        report.add(triggers, 1, "V040", "missing triggers.jsonl")
        return
    positive = negative = 0
    seen: set[str] = set()
    for number, raw in enumerate(triggers.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            report.add(triggers, number, "V041", f"invalid JSON: {exc.msg}")
            continue
        query, flag = row.get("query"), row.get("should_trigger")
        if not isinstance(query, str) or not query.strip() or not isinstance(flag, bool):
            report.add(
                triggers,
                number,
                "V042",
                "each row needs a 'query' string and a boolean 'should_trigger'",
            )
            continue
        if query in seen:
            report.add(triggers, number, "V043", "duplicate query")
        seen.add(query)
        positive += flag
        negative += not flag
    if positive < MIN_TRIGGER_ROWS or negative < MIN_TRIGGER_ROWS:
        report.add(
            triggers,
            1,
            "V044",
            f"needs at least {MIN_TRIGGER_ROWS} positive and {MIN_TRIGGER_ROWS} negative rows "
            f"(has {positive} and {negative})",
        )
    cases = evals / skill.name / "cases.json"
    if not cases.is_file():
        report.add(cases, 1, "V045", "missing cases.json with functional cases")
        return
    try:
        data = json.loads(cases.read_text(encoding="utf-8"))
        assert isinstance(data.get("cases"), list) and data["cases"]
        for case in data["cases"]:
            assert case.get("id") and case.get("prompt") and case.get("assertions")
    except (json.JSONDecodeError, AssertionError, AttributeError):
        report.add(
            cases,
            1,
            "V046",
            "cases.json needs a non-empty 'cases' list with id, prompt, assertions",
        )


def _check_vendored(skill: Path, lib: Path, report: Report) -> None:
    vendored = skill / "scripts" / "kitlib"
    if not vendored.is_dir():
        return
    for source in sorted(lib.glob("*.py")):
        copy = vendored / source.name
        if not copy.is_file() or copy.read_bytes() != source.read_bytes():
            report.add(copy, 1, "V050", f"vendored copy of {source.name} differs from lib/kitlib")


def validate_skill(skill: Path, evals: Path, lib: Path, report: Report) -> None:
    md = skill / "SKILL.md"
    if not md.is_file():
        report.add(skill, 1, "V000", "SKILL.md is missing (the name is case-sensitive)")
        return
    text = md.read_text(encoding="utf-8")
    if text.startswith("\ufeff") or "\r\n" in text:
        report.add(md, 1, "V027", "use UTF-8 without a byte order mark and LF line endings")
    parsed = frontmatter.parse(text)
    _check_front_matter(skill, parsed, report)
    if parsed.fm is not None:
        _check_body(skill, parsed, report)
    _check_scripts(skill, report)
    _check_evals(skill, evals, report)
    _check_vendored(skill, lib, report)


def _check_siblings(skills: list[Path], report: Report) -> None:
    """Flag trigger queries that read as a positive for one skill but are written for another."""
    seen: dict[str, str] = {}
    for skill in skills:
        for query in _positive_queries(skill):
            if query in seen and seen[query] != skill.name:
                report.add(
                    skill, 1, "V060", f"positive query also claimed by {seen[query]}: '{query}'"
                )
            seen[query] = skill.name


def _positive_queries(skill: Path) -> list[str]:
    path = skill.parent.parent / "evals" / skill.name / "triggers.jsonl"
    if not path.is_file():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if row.get("should_trigger") is True and isinstance(row.get("query"), str):
            out.append(row["query"])
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Specwright skill folders.")
    parser.add_argument("--root", default=".", help="kit root holding skills/, evals/ and lib/")
    parser.add_argument("skills", nargs="*", help="skill names to check (default: all)")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        print(f"error: {skills_dir} not found", file=sys.stderr)
        return 2
    all_skills = sorted(
        p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith("_")
    )
    chosen = [p for p in all_skills if not args.skills or p.name in args.skills]
    if args.skills and len(chosen) != len(set(args.skills)):
        print(f"error: unknown skill in {args.skills}", file=sys.stderr)
        return 2
    report = Report(root)
    for skill in chosen:
        validate_skill(skill, root / "evals", root / "lib" / "kitlib", report)
    _check_siblings(chosen, report)
    for finding in report.items:
        print(finding, file=sys.stderr if finding.error else sys.stdout)
    warnings = len(report.items) - len(report.errors)
    print(f"{len(chosen)} skill(s) checked, {len(report.errors)} error(s), {warnings} warning(s)")
    return 1 if report.errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except miniyaml.YamlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)
