"""Light inventory of an existing project: names and pointers only, never file bodies.

For every code root it lists endpoints, screens, entities and tests with ``path:line``; for the
docs it lists headings. It then groups the names into candidate features by shared keywords
(``/refunds`` + ``Refund`` entity + ``RefundPage`` + ``refund.test.ts`` → ``refund``). The output
is a map to choose what to analyse in depth; it is not evidence of behaviour.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

SKIP = {
    ".git",
    "node_modules",
    ".specwright",
    ".venv",
    "venv",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    "__pycache__",
    ".gradle",
    ".idea",
    ".dart_tool",
    "vendor",
    "bin",
    "obj",
}
CODE_EXT = {
    ".java",
    ".kt",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".go",
    ".dart",
    ".cs",
    ".rb",
    ".php",
    ".vue",
    ".svelte",
    ".prisma",
    ".sql",
}
MAX_FILES = 20000
MAX_BYTES = 300_000

HTTP = r"(get|post|put|delete|patch)"
ENDPOINT_RX = [
    (
        "spring",
        re.compile(
            r"@(Get|Post|Put|Delete|Patch|Request)Mapping\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?\"([^\"]*)\""
        ),
    ),
    ("nest", re.compile(r"@(Get|Post|Put|Delete|Patch)\(\s*['\"]([^'\"]*)['\"]")),
    ("express", re.compile(rf"\b(?:app|router|server|api)\.{HTTP}\(\s*['\"`]([^'\"`]+)['\"`]")),
    ("python", re.compile(rf"@(?:\w+)\.{HTTP}\(\s*['\"]([^'\"]+)['\"]")),
    ("flask", re.compile(r"@(?:\w+)\.route\(\s*['\"]([^'\"]+)['\"]")),
    ("django", re.compile(r"\b(?:re_)?path\(\s*r?['\"]([^'\"]*)['\"]")),
    ("go", re.compile(r"\b(?:HandleFunc|Handle|GET|POST|PUT|DELETE|PATCH)\(\s*\"([^\"]+)\"")),
]
CLASS_PREFIX = re.compile(
    r"@(?:RequestMapping|Controller)\s*\(\s*(?:value\s*=\s*|path\s*=\s*)?['\"]([^'\"]*)['\"]"
)
ENTITY_RX = [
    re.compile(r"@Entity[\s\S]{0,200}?\bclass\s+(\w+)"),
    re.compile(r"^model\s+(\w+)\s*\{", re.M),
    re.compile(r"^class\s+(\w+)\((?:models\.Model|Base|db\.Model|SQLModel)", re.M),
    re.compile(r"create\s+table\s+(?:if\s+not\s+exists\s+)?[`\"]?(\w+)", re.I),
]
SCREEN_RX = [
    re.compile(r"<Route\s+[^>]*path=['\"]([^'\"]+)['\"]"),
    re.compile(r"\bpath:\s*['\"](/[^'\"]*)['\"]"),
    re.compile(r"class\s+(\w+(?:Screen|Page|View))\s+extends\s+(?:StatelessWidget|StatefulWidget)"),
]
TEST_NAME_RX = [
    re.compile(r"\b(?:it|test|describe)\(\s*['\"`]([^'\"`]{3,120})['\"`]"),
    re.compile(r"@Test[\s\S]{0,120}?void\s+(\w+)\s*\("),
    re.compile(r"^\s*def\s+(test_\w+)\s*\(", re.M),
    re.compile(r"^func\s+(Test\w+)\s*\(", re.M),
    re.compile(r"\btestWidgets?\(\s*['\"]([^'\"]{3,120})['\"]"),
]
TEST_FILE = re.compile(
    r"(\.test\.|\.spec\.|_test\.|Test\.java$|Tests\.java$|^test_.*\.py$|Test\.kt$|_test\.dart$)"
)
STOP = {
    "api",
    "v1",
    "v2",
    "v3",
    "index",
    "page",
    "pages",
    "screen",
    "view",
    "controller",
    "service",
    "test",
    "tests",
    "spec",
    "id",
    "app",
    "src",
    "main",
    "java",
    "com",
    "org",
    "lib",
    "util",
    "utils",
    "helper",
    "helpers",
    "component",
    "components",
    "the",
    "and",
    "for",
    "with",
    "should",
    "when",
    "then",
    "given",
    "new",
    "get",
    "post",
    "put",
    "delete",
    "patch",
    "list",
    "create",
    "update",
    "find",
    "all",
    "by",
    "to",
    "of",
    "in",
    "on",
    "is",
    "a",
    "an",
    "it",
    "be",
    "returns",
    "return",
    "can",
    "not",
    "route",
    "routes",
    "router",
    "model",
    "models",
    "entity",
    "dto",
    "impl",
    "default",
    "base",
    "core",
    "common",
    "config",
    "module",
    "layout",
    "home",
    "root",
}


def _words(text: str) -> list[str]:
    text = re.sub(r"[:{<\[].*?[}>\]]", " ", text)  # drop path parameters
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    out = []
    for w in re.split(r"[^A-Za-z0-9]+", text.lower()):
        if len(w) < 3 or w in STOP or w.isdigit():
            continue
        if w.endswith("ies") and len(w) > 4:
            w = w[:-3] + "y"
        elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        out.append(w)
    return out


def _line(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _files(root: Path):
    count = 0
    for p in sorted(root.rglob("*")):
        if count >= MAX_FILES:
            return
        rel = p.relative_to(root)
        if any(
            part in SKIP or (part.startswith(".") and part not in (".", ".."))
            for part in rel.parts[:-1]
        ):
            continue
        if not p.is_file() or p.suffix not in CODE_EXT:
            continue
        try:
            if p.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        count += 1
        yield p, rel.as_posix()


def _fs_route(rel: str) -> str | None:
    """Next.js / SvelteKit / Nuxt file-system routes."""
    m = re.search(r"(?:^|/)(?:src/)?(pages|app|routes)/(.+)$", rel)
    if not m:
        return None
    path = m.group(2)
    path = re.sub(r"\.(tsx|jsx|ts|js|vue|svelte)$", "", path)
    path = re.sub(r"(^|/)(index|page|route|\+page|\+server)$", "", path)
    path = re.sub(r"\(([^)]+)\)/?", "", path)  # route groups
    return "/" + path.strip("/")


def scan_code(root: Path, name: str) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {
        "endpoints": [],
        "screens": [],
        "entities": [],
        "tests": [],
    }
    for path, rel in _files(root):
        where = f"{name}/{rel}"
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        is_test = (
            bool(TEST_FILE.search(path.name)) or "/test/" in f"/{rel}" or "/__tests__/" in f"/{rel}"
        )
        if is_test:
            names = []
            for rx in TEST_NAME_RX:
                for m in rx.finditer(text):
                    names.append({"name": m.group(1), "at": f"{where}:{_line(text, m.start())}"})
            found["tests"].append({"file": where, "count": len(names), "names": names[:12]})
            continue
        fs = _fs_route(rel)
        if fs is not None and path.suffix in {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte"}:
            kind = (
                "endpoints"
                if "/api/" in f"/{rel}" or path.stem in ("route", "+server")
                else "screens"
            )
            found[kind].append({"name": fs, "at": f"{where}:1", "via": "file route"})
        prefix = ""
        cp = CLASS_PREFIX.search(text)
        if cp and path.suffix in {".java", ".kt", ".ts"}:
            prefix = cp.group(1).rstrip("/")
        for via, rx in ENDPOINT_RX:
            for m in rx.finditer(text):
                groups = m.groups()
                verb = groups[0].upper() if len(groups) == 2 else ""
                route = groups[-1]
                if via in ("spring", "nest"):
                    if verb == "REQUEST" and m.start() == (cp.start() if cp else -1):
                        continue
                    route = prefix + ("/" + route.lstrip("/") if route else "")
                    verb = "" if verb == "REQUEST" else verb
                if via == "django" and path.name != "urls.py":
                    continue
                found["endpoints"].append(
                    {
                        "name": f"{verb} {route}".strip() or "/",
                        "at": f"{where}:{_line(text, m.start())}",
                        "via": via,
                    }
                )
        for rx in ENTITY_RX:
            if rx.pattern.startswith("create") and path.suffix != ".sql":
                continue
            for m in rx.finditer(text):
                found["entities"].append(
                    {"name": m.group(1), "at": f"{where}:{_line(text, m.start())}"}
                )
        for rx in SCREEN_RX:
            for m in rx.finditer(text):
                if (
                    rx.pattern.startswith("\\bpath")
                    and "router" not in rel.lower()
                    and "routes" not in rel.lower()
                ):
                    continue
                found["screens"].append(
                    {"name": m.group(1), "at": f"{where}:{_line(text, m.start())}"}
                )
    return found


def scan_docs(folders: list[tuple[Path, str]]) -> list[dict[str, Any]]:
    out = []
    for folder, label in folders:
        if not folder.is_dir():
            continue
        for p in sorted(folder.rglob("*.md"))[:400]:
            rel = p.relative_to(folder).as_posix()
            if any(
                part in SKIP or part == "raw" or part.startswith(".")
                for part in Path(rel).parts[:-1]
            ):
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                m = re.match(r"^(#{1,3})\s+(.+?)\s*#*$", line)
                if m:
                    out.append(
                        {
                            "name": m.group(2)[:100],
                            "at": f"{label}/{rel}:{n}",
                            "level": len(m.group(1)),
                        }
                    )
    return out


def candidates(code: dict[str, dict], docs: list[dict], limit: int = 40) -> list[dict[str, Any]]:
    """Group names into candidate features by shared keyword across kinds."""
    hits: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for kinds in code.values():
        for kind, rows in kinds.items():
            for row in rows:
                label = row.get("name") or row.get("file", "")
                if kind == "tests":
                    label = row["file"].rsplit("/", 1)[-1]
                for w in set(_words(label)):
                    hits[w][kind].append(row.get("at") or row.get("file"))
    for row in docs:
        for w in set(_words(row["name"])):
            hits[w]["docs"].append(row["at"])
    out = []
    for word, kinds in hits.items():
        total = sum(len(v) for v in kinds.values())
        if len(kinds) < 2 and total < 3:
            continue
        out.append(
            {
                "name": word,
                "kinds": {k: len(v) for k, v in sorted(kinds.items())},
                "score": len(kinds) * 10 + min(total, 30),
                "pointers": [p for v in kinds.values() for p in v[:2]][:8],
            }
        )
    out.sort(key=lambda c: (-c["score"], c["name"]))
    return out[:limit]


def render(inv: dict[str, Any]) -> str:
    """Compact Markdown for agents: counts, candidates, then pointers."""
    lines = [
        "# Inventory",
        "",
        f"Generated: {inv['date']} · names and pointers only; not evidence of behaviour.",
        "",
    ]
    lines.append("## Code roots")
    if not inv["roots"]:
        lines.append("None — no code registered; the actual side of every analysis is empty.")
    for r in inv["roots"]:
        c = inv["code"].get(r["name"], {})
        lines.append(
            f"- {r['name']} ({r['path'] or '.'}): {len(c.get('endpoints', []))} endpoints, "
            f"{len(c.get('screens', []))} screens, {len(c.get('entities', []))} entities, "
            f"{sum(t['count'] for t in c.get('tests', []))} tests "
            f"in {len(c.get('tests', []))} files"
        )
    lines += ["", f"Doc headings: {len(inv['docs'])}", "", "## Candidate features", ""]
    lines.append("| Candidate | Found in | Pointers |")
    lines.append("| --- | --- | --- |")
    for c in inv["candidates"]:
        kinds = ", ".join(f"{k} {n}" for k, n in c["kinds"].items())
        lines.append(f"| {c['name']} | {kinds} | {'; '.join(c['pointers'][:4])} |")
    for r in inv["roots"]:
        c = inv["code"].get(r["name"], {})
        for kind in ("endpoints", "screens", "entities"):
            rows = c.get(kind, [])
            if rows:
                lines += ["", f"## {r['name']} {kind}", ""]
                lines += [f"- {x['name']} — {x['at']}" for x in rows[:80]]
                if len(rows) > 80:
                    lines.append(f"- … {len(rows) - 80} more in .metadata/inventory.json")
    return "\n".join(lines) + "\n"
