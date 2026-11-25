"""Technology stack profile: detect it from the code, lock it, and check tasks against it.

The profile lives in ``stack.yaml`` beside a project's ``project.yaml``; a program may keep one
at its root, inherited by every project (a project layer replaces the program layer of the same
name). Stories never name technology (sw-shape's leakage rule); the stack binds plans, tasks
and the prompts given to implementing agents.

A locked profile carries ``locked.hash``, the hash of its content. Locking needs that hash back
as confirmation, so a yes is bound to the exact profile shown. Any later change unlocks it and
is logged in ``history`` with a reason.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from kitlib import fsio, miniyaml, workspace

FILE = "stack.yaml"
SCHEMA_VERSION = 1
CODE_LAYERS = ("backend", "frontend", "mobile", "data", "devops")
LAYER_KEYS = ("language", "version", "framework", "framework_version", "build", "test", "notes")

# Known technologies: name -> (layer, aliases). Used to detect stray technology in tasks.
CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "java": ("backend", ()),
    "kotlin": ("backend", ()),
    "spring-boot": ("backend", ("spring boot", "springboot")),
    "quarkus": ("backend", ()),
    "micronaut": ("backend", ()),
    "node": ("backend", ("node.js", "nodejs")),
    "express": ("backend", ("express.js", "expressjs")),
    "nestjs": ("backend", ("nest.js",)),
    "fastify": ("backend", ()),
    "python": ("backend", ()),
    "django": ("backend", ()),
    "fastapi": ("backend", ()),
    "flask": ("backend", ()),
    "go": ("backend", ("golang",)),
    "gin": ("backend", ()),
    "dotnet": ("backend", (".net", "asp.net", "c#")),
    "ruby": ("backend", ()),
    "rails": ("backend", ("ruby on rails",)),
    "php": ("backend", ()),
    "laravel": ("backend", ()),
    "rust": ("backend", ()),
    "react": ("frontend", ("reactjs", "react.js")),
    "next": ("frontend", ("next.js", "nextjs")),
    "vue": ("frontend", ("vue.js", "vuejs")),
    "nuxt": ("frontend", ()),
    "angular": ("frontend", ()),
    "svelte": ("frontend", ("sveltekit",)),
    "typescript": ("frontend", ()),
    "tailwind": ("frontend", ("tailwindcss",)),
    "flutter": ("mobile", ()),
    "react-native": ("mobile", ("react native",)),
    "swift": ("mobile", ("swiftui",)),
    "postgres": ("data", ("postgresql",)),
    "mysql": ("data", ("mariadb",)),
    "mongodb": ("data", ("mongo",)),
    "redis": ("data", ()),
    "elasticsearch": ("data", ("opensearch",)),
    "kafka": ("data", ()),
    "rabbitmq": ("data", ()),
    "sqlite": ("data", ()),
    "docker": ("devops", ()),
    "kubernetes": ("devops", ("k8s",)),
    "terraform": ("devops", ()),
    "github-actions": ("devops", ("github actions",)),
    "gitlab-ci": ("devops", ("gitlab ci",)),
    "aws": ("devops", ()),
    "gcp": ("devops", ("google cloud",)),
    "azure": ("devops", ()),
}


class StackError(ValueError):
    """The request is invalid or would bypass the lock."""


def _today() -> str:
    return datetime.date.today().isoformat()


def path_for(root: Path, scope: str | None) -> Path:
    return (workspace.scope_dir(root, scope) if scope else root) / FILE


def empty() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "proposed",
        "layers": {},
        "libraries": {"allowed": [], "forbidden": [], "needs_approval": []},
        "conventions": [],
        "history": [],
    }


def load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = miniyaml.loads(path.read_text(encoding="utf-8"))
    base = empty()
    base.update(data)
    return base


def save(path: Path, data: dict[str, Any]) -> None:
    fsio.atomic_write(path, miniyaml.dumps(data))


def content_hash(data: dict[str, Any]) -> str:
    body = {k: data.get(k) for k in ("layers", "libraries", "conventions")}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()[:12]


def effective(root: Path, scope: str | None) -> dict[str, Any] | None:
    """Program profile merged with the project profile; None when neither exists."""
    program = load(root / FILE) if scope and workspace.mode_of(root) == "program" else None
    project = load(path_for(root, scope))
    if program is None and project is None:
        return None
    merged = empty()
    for part in (program, project):
        if not part:
            continue
        merged["layers"].update(part.get("layers") or {})
        for key in ("allowed", "forbidden", "needs_approval"):
            merged["libraries"][key] = sorted(
                set(merged["libraries"][key]) | set((part.get("libraries") or {}).get(key) or [])
            )
        merged["conventions"] += [c for c in part.get("conventions") or [] if c]
    owner = project or program
    merged["status"] = owner.get("status", "proposed")
    merged["locked"] = owner.get("locked")
    merged["source"] = "project" if project else "program"
    if program and project:
        merged["source"] = "program+project"
        # A project lock only counts when the program part it inherits is locked too.
        if program.get("status") != "locked":
            merged["status"] = "proposed"
    return merged


# ---- detection ---------------------------------------------------------------------------------


def _line_of(text: str, needle: str) -> int:
    for number, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return number
    return 1


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _major(version: str) -> str:
    m = re.search(r"\d+(\.\d+)?", version or "")
    return m.group(0) if m else ""


def detect(code: Path) -> dict[str, Any]:
    """Proposed layers with evidence (file:line), read from build and config files only."""
    layers: dict[str, dict[str, Any]] = {}
    seen_data: list[str] = []

    def put(layer: str, evidence: str, **values: str) -> None:
        entry = layers.setdefault(layer, {"evidence": []})
        for k, v in values.items():
            if v and not entry.get(k):
                entry[k] = v
        if evidence not in entry["evidence"]:
            entry["evidence"].append(evidence)

    def rel(p: Path) -> str:
        return p.relative_to(code).as_posix()

    skip = {"node_modules", ".git", ".venv", "venv", "dist", "build", "target", ".specwright"}
    files = [
        p
        for p in sorted(code.rglob("*"))
        if p.is_file()
        and not any(part in skip for part in p.relative_to(code).parts)
        and len(p.relative_to(code).parts) <= 4
    ]
    for p in files:
        name, text = p.name, None
        if name == "pom.xml":
            text = _read(p)
            java = re.search(r"<(?:java\.version|maven\.compiler\.release)>([^<]+)<", text)
            boot = re.search(
                r"<artifactId>spring-boot-starter-parent</artifactId>\s*<version>([^<]+)<", text
            )
            put(
                "backend",
                f"{rel(p)}:{_line_of(text, java.group(0) if java else '<project')}",
                language="java",
                version=java.group(1).strip() if java else "",
                framework="spring-boot" if "spring-boot" in text else "",
                framework_version=_major(boot.group(1)) if boot else "",
                build="maven",
                test="mvn test",
            )
        elif name in ("build.gradle", "build.gradle.kts"):
            text = _read(p)
            boot = re.search(
                r"org\.springframework\.boot['\"]?\)?\s*version\s*['\"]([^'\"]+)", text
            )
            java = re.search(
                r"(?:JavaLanguageVersion\.of\(|sourceCompatibility\s*=\s*['\"]?(?:JavaVersion\.VERSION_)?)(\d+)",
                text,
            )
            put(
                "backend",
                f"{rel(p)}:1",
                language="kotlin" if name.endswith(".kts") and "kotlin(" in text else "java",
                version=java.group(1) if java else "",
                framework="spring-boot" if "springframework.boot" in text else "",
                framework_version=_major(boot.group(1)) if boot else "",
                build="gradle",
                test="./gradlew test",
            )
        elif name == "package.json":
            text = _read(p)
            try:
                pkg = json.loads(text)
            except ValueError:
                continue
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            node = (pkg.get("engines") or {}).get("node", "")
            test = "npm test" if (pkg.get("scripts") or {}).get("test") else ""
            front = next(
                (
                    f
                    for f in ("next", "nuxt", "react", "vue", "@angular/core", "svelte")
                    if f in deps
                ),
                "",
            )
            if front:
                fw = {"@angular/core": "angular"}.get(front, front)
                put(
                    "frontend",
                    f"{rel(p)}:{_line_of(text, chr(34) + front + chr(34))}",
                    language="typescript" if "typescript" in deps else "javascript",
                    version=_major(node),
                    framework=fw,
                    framework_version=_major(deps[front]),
                    build="npm",
                    test=test,
                )
            if "react-native" in deps:
                put(
                    "mobile",
                    f"{rel(p)}:{_line_of(text, 'react-native')}",
                    framework="react-native",
                    framework_version=_major(deps["react-native"]),
                )
            back = next((f for f in ("@nestjs/core", "express", "fastify", "koa") if f in deps), "")
            if back:
                fw = {"@nestjs/core": "nestjs"}.get(back, back)
                put(
                    "backend",
                    f"{rel(p)}:{_line_of(text, chr(34) + back + chr(34))}",
                    language="typescript" if "typescript" in deps else "javascript",
                    version=_major(node),
                    framework=fw,
                    framework_version=_major(deps[back]),
                    build="npm",
                    test=test,
                )
        elif name in (".nvmrc", ".node-version"):
            v = _major(_read(p).strip())
            for layer in ("frontend", "backend"):
                if (
                    layer in layers
                    and layers[layer].get("build") == "npm"
                    and not layers[layer].get("version")
                ):
                    layers[layer]["version"] = v
        elif name in ("pyproject.toml", "requirements.txt", "setup.cfg"):
            text = _read(p).lower()
            fw = next(
                (f for f in ("fastapi", "django", "flask") if re.search(rf"\b{f}\b", text)), ""
            )
            py = re.search(r"requires-python\s*=\s*['\"][^0-9]*([0-9.]+)", text)
            put(
                "backend",
                f"{rel(p)}:{_line_of(text, fw) if fw else 1}",
                language="python",
                version=_major(py.group(1)) if py else "",
                framework=fw,
                build="pip"
                if name == "requirements.txt"
                else ("poetry" if "[tool.poetry" in text else "pip"),
                test="pytest" if "pytest" in text else "",
            )
        elif name == "go.mod":
            text = _read(p)
            go = re.search(r"^go\s+([0-9.]+)", text, re.M)
            fw = "gin" if "gin-gonic/gin" in text else ""
            put(
                "backend",
                f"{rel(p)}:1",
                language="go",
                version=go.group(1) if go else "",
                framework=fw,
                build="go",
                test="go test ./...",
            )
        elif name == "pubspec.yaml":
            text = _read(p)
            if "flutter" in text:
                sdk = re.search(r"sdk:\s*['\"]?[>=^]*\s*([0-9.]+)", text)
                put(
                    "mobile",
                    f"{rel(p)}:{_line_of(text, 'flutter')}",
                    language="dart",
                    version=_major(sdk.group(1)) if sdk else "",
                    framework="flutter",
                    build="flutter",
                    test="flutter test",
                )
        elif name.endswith(".csproj"):
            text = _read(p)
            tf = re.search(r"<TargetFramework>net([0-9.]+)<", text)
            put(
                "backend",
                f"{rel(p)}:1",
                language="csharp",
                version=tf.group(1) if tf else "",
                framework="aspnet" if "Microsoft.NET.Sdk.Web" in text else "",
                build="dotnet",
                test="dotnet test",
            )
        elif name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
            text = _read(p).lower()
            for img, tech in (
                ("postgres", "postgres"),
                ("mysql", "mysql"),
                ("mariadb", "mysql"),
                ("mongo", "mongodb"),
                ("redis", "redis"),
                ("kafka", "kafka"),
                ("rabbitmq", "rabbitmq"),
                ("elasticsearch", "elasticsearch"),
            ):
                if f"image: {img}" in text or f'image: "{img}' in text or f"/{img}:" in text:
                    if tech not in seen_data:
                        seen_data.append(tech)
                        put("data", f"{rel(p)}:{_line_of(text, img)}")
            put("devops", f"{rel(p)}:1", framework="docker")
        elif name == "Dockerfile":
            put("devops", f"{rel(p)}:1", framework="docker")
        elif name.endswith(".tf"):
            put("devops", f"{rel(p)}:1", build="terraform")
        elif p.parent.name == "workflows" and p.parent.parent.name == ".github":
            put("devops", f"{rel(p)}:1", notes="github-actions")
    if seen_data:
        layers["data"]["framework"] = ", ".join(seen_data)
    return layers


# ---- edits ------------------------------------------------------------------------------------


def _unlock(data: dict[str, Any], change: str, reason: str | None) -> None:
    if data.get("status") == "locked":
        if not reason:
            raise StackError("the stack is locked; pass --reason to change it (it unlocks)")
        data["status"] = "proposed"
        data.pop("locked", None)
    data.setdefault("history", []).append(
        {"date": _today(), "change": change, "reason": reason or "initial profile"}
    )


def apply_detected(data: dict[str, Any], detected: dict[str, Any], reason: str | None) -> None:
    _unlock(data, "detected layers: " + ", ".join(sorted(detected)), reason)
    for layer, values in detected.items():
        current = data["layers"].setdefault(layer, {})
        for k, v in values.items():
            if v and not current.get(k):
                current[k] = v


def set_value(data: dict[str, Any], key: str, value: str, reason: str | None) -> None:
    layer, _, field = key.partition(".")
    if layer not in CODE_LAYERS + ("qa", "design", "docs") or field not in LAYER_KEYS:
        raise StackError(f"key must be <layer>.<field>; fields: {', '.join(LAYER_KEYS)}")
    _unlock(data, f"{key} = {value}", reason)
    data["layers"].setdefault(layer, {})[field] = value


def set_library(data: dict[str, Any], kind: str, name: str, reason: str | None) -> None:
    _unlock(data, f"{kind} += {name}", reason)
    libs = data["libraries"]
    for k in ("allowed", "forbidden", "needs_approval"):
        libs[k] = [x for x in libs.get(k) or [] if x != name]
    libs[kind] = sorted({*libs.get(kind, []), name})


def add_convention(data: dict[str, Any], text: str, reason: str | None) -> None:
    _unlock(data, "convention added", reason)
    data["conventions"].append(text)


def lock(data: dict[str, Any], confirm: str | None) -> dict[str, Any]:
    """Preview (no confirm) or lock; confirm must equal the content hash just shown."""
    digest = content_hash(data)
    missing = [
        layer
        for layer, v in data["layers"].items()
        if layer in CODE_LAYERS and not v.get("framework") and not v.get("language")
    ]
    if not data["layers"]:
        raise StackError("no layers; run detect --write or set values first")
    if confirm is None:
        return {"applied": False, "hash": digest, "incomplete_layers": missing}
    if confirm != digest:
        raise StackError(f"confirmation {confirm} does not match the current profile {digest}")
    data["status"] = "locked"
    data["locked"] = {"hash": digest, "by": "owner (self)", "date": _today()}
    data.setdefault("history", []).append({"date": _today(), "change": "locked", "reason": digest})
    return {"applied": True, "hash": digest, "incomplete_layers": missing}


# ---- checks -----------------------------------------------------------------------------------


# Names that are also ordinary words match only in these exact, case-sensitive spellings.
AMBIGUOUS = {
    "go": ("Golang", "golang", "Go 1."),
    "next": ("Next.js", "NextJS", "nextjs"),
    "react": ("React", "ReactJS", "React.js"),
    "express": ("Express.js", "ExpressJS", "expressjs"),
    "node": ("Node.js", "NodeJS", "nodejs"),
    "swift": ("Swift", "SwiftUI"),
    "rust": ("Rust",),
    "gin": ("Gin",),
    "ruby": ("Ruby",),
    "flask": ("Flask",),
    "rails": ("Rails", "Ruby on Rails"),
    "vue": ("Vue", "Vue.js", "vuejs"),
    "angular": ("Angular",),
    "svelte": ("Svelte", "SvelteKit"),
}


# A framework brings its runtime and language with it.
IMPLIES = {
    "spring-boot": {"java"},
    "quarkus": {"java"},
    "micronaut": {"java"},
    "nestjs": {"node", "typescript"},
    "express": {"node"},
    "fastify": {"node"},
    "next": {"react", "node"},
    "nuxt": {"vue", "node"},
    "react-native": {"react", "node"},
    "django": {"python"},
    "fastapi": {"python"},
    "flask": {"python"},
    "gin": {"go"},
    "rails": {"ruby"},
    "laravel": {"php"},
}


def _mentions(text: str) -> set[str]:
    """Catalog technologies a free text names."""
    found = set()
    low = text.lower()
    for name, (_layer, aliases) in CATALOG.items():
        if name in AMBIGUOUS:
            if any(
                re.search(r"(?<![\w])" + re.escape(w) + r"(?![\w])", text) for w in AMBIGUOUS[name]
            ):
                found.add(name)
            continue
        for word in (name, *aliases):
            if re.search(r"(?<![\w.-])" + re.escape(word) + r"(?![\w-])", low):
                found.add(name)
                break
    return found


def _canon(value: str) -> set[str]:
    """Catalog names a profile value stands for ('react', 'Spring Boot', 'postgres, redis')."""
    out = set()
    for part in re.split(r"[,;/]| \+ ", value.lower()):
        part = part.strip()
        for name, (_layer, aliases) in CATALOG.items():
            if part == name or part in aliases:
                out.add(name)
    return out | _mentions(value)


def _profile_words(profile: dict[str, Any]) -> set[str]:
    words: set[str] = set()
    for values in (profile.get("layers") or {}).values():
        for key, v in values.items():
            if key == "evidence":
                continue
            for item in v if isinstance(v, list) else [v]:
                if isinstance(item, str):
                    words |= _canon(item)
    for lib in (profile.get("libraries") or {}).get("allowed") or []:
        words |= _canon(lib)
    for name in list(words):
        words |= IMPLIES.get(name, set())
    return words


def check_tasks(profile: dict[str, Any] | None, blocks: dict, layer_of) -> list[str]:
    """Findings for one tasks file: missing Stack lines, stray or forbidden technology."""
    if profile is None:
        return ["no stack profile: run stack.py detect --write, review it, then lock it"]
    findings = []
    if profile.get("status") != "locked":
        findings.append("stack profile is not locked; lock it before implementation starts")
    known = _profile_words(profile)
    libs = profile.get("libraries") or {}
    for tid, block in blocks.items():
        layer = layer_of(block.title)
        text = " ".join([block.title, *block.fields.values()])
        if layer in CODE_LAYERS and layer in (profile.get("layers") or {}):
            if not block.field_line("Stack"):
                findings.append(f"{tid}: Stack line missing (layer {layer})")
        for tech in sorted(_mentions(text) - known):
            findings.append(f"{tid}: names {tech}, which is not in the locked stack")
        low = text.lower()
        for lib in libs.get("forbidden") or []:
            if lib.lower() in low:
                findings.append(f"{tid}: uses forbidden library {lib}")
        for lib in libs.get("needs_approval") or []:
            if lib.lower() in low:
                findings.append(f"{tid}: {lib} needs approval before use (stop and ask)")
    return findings


def layer_line(profile: dict[str, Any] | None, layer: str | None) -> str:
    """One `Stack:` value, e.g. 'java 21 · spring-boot 3.3 · maven · test: mvn test'."""
    if not profile or not layer:
        return ""
    v = (profile.get("layers") or {}).get(layer) or {}
    parts = [
        " ".join(x for x in (v.get("language"), v.get("version")) if x),
        " ".join(x for x in (v.get("framework"), v.get("framework_version")) if x),
        v.get("build", ""),
        f"test: {v['test']}" if v.get("test") else "",
    ]
    return " · ".join(p for p in parts if p)
