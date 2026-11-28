"""Project foundation: the first story of a new codebase (structure, format, lint, tests with
coverage, one `make check` gate, CI, and an AI workflow file for coding agents).

Tooling choices are asked at runtime, prefilled from the stack, and saved in `stack.yaml` under
`tooling`. Defaults are well-known, widely used tools; versions are never pinned here: the
implementing agent pins current stable versions from official docs when it sets them up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Per language: options per concern, first option is the default.
CATALOG: dict[str, dict[str, Any]] = {
    "java": {
        "build": ["maven", "gradle"],
        "format": ["spotless (google-java-format)", "spotless (palantir-java-format)"],
        "lint": ["checkstyle + spotbugs", "checkstyle", "errorprone"],
        "test": ["junit5 + jacoco", "junit5 + jacoco + testcontainers"],
        "cmd": {
            "maven": {
                "setup": "./mvnw -q -DskipTests install",
                "fmt": "./mvnw -q spotless:apply",
                "fmt-check": "./mvnw -q spotless:check",
                "lint": "./mvnw -q checkstyle:check spotbugs:check",
                "test": "./mvnw -q verify",
                "build": "./mvnw -q -DskipTests package",
                "coverage-report": "target/site/jacoco/index.html",
            },
            "gradle": {
                "setup": "./gradlew --quiet build -x test",
                "fmt": "./gradlew --quiet spotlessApply",
                "fmt-check": "./gradlew --quiet spotlessCheck",
                "lint": "./gradlew --quiet checkstyleMain spotbugsMain",
                "test": "./gradlew --quiet test jacocoTestCoverageVerification",
                "build": "./gradlew --quiet assemble",
                "coverage-report": "build/reports/jacoco/test/html/index.html",
            },
        },
        "structure": "src/main/java/<group>/<app>/{api,domain,infra}, src/test/java mirrors main",
    },
    "kotlin": {
        "build": ["gradle"],
        "format": ["spotless (ktlint)"],
        "lint": ["detekt"],
        "test": ["junit5 + kover"],
        "cmd": {
            "gradle": {
                "setup": "./gradlew --quiet dependencies",
                "fmt": "./gradlew --quiet spotlessApply",
                "fmt-check": "./gradlew --quiet spotlessCheck",
                "lint": "./gradlew --quiet detekt",
                "typecheck": "./gradlew --quiet compileKotlin compileTestKotlin",
                "test": "./gradlew --quiet test koverVerify",
                "build": "./gradlew --quiet assemble",
                "coverage-report": "build/reports/kover/html/index.html",
            }
        },
        "structure": "src/main/kotlin/<package>, src/test/kotlin mirrors main",
    },
    "typescript": {
        "build": ["pnpm", "npm"],
        "format": ["prettier", "biome"],
        "lint": ["eslint (typescript-eslint)", "biome"],
        "test": ["vitest + v8 coverage", "jest + istanbul"],
        "cmd": {
            "pnpm": {
                "setup": "pnpm install --frozen-lockfile",
                "fmt": "pnpm exec prettier --write .",
                "fmt-check": "pnpm exec prettier --check .",
                "lint": "pnpm exec eslint . --max-warnings 0",
                "typecheck": "pnpm exec tsc --noEmit",
                "test": "pnpm exec vitest run --coverage",
                "build": "pnpm build",
                "coverage-report": "coverage/index.html",
            },
            "npm": {
                "setup": "npm ci",
                "fmt": "npx prettier --write .",
                "fmt-check": "npx prettier --check .",
                "lint": "npx eslint . --max-warnings 0",
                "typecheck": "npx tsc --noEmit",
                "test": "npx vitest run --coverage",
                "build": "npm run build",
                "coverage-report": "coverage/index.html",
            },
        },
        "structure": "src/{app,features/<name>,shared}, tests beside code as *.test.ts",
    },
    "javascript": {
        "build": ["npm", "pnpm"],
        "format": ["prettier"],
        "lint": ["eslint"],
        "test": ["vitest + v8 coverage"],
        "cmd": {
            "npm": {
                "setup": "npm ci",
                "fmt": "npm exec -- prettier --write .",
                "fmt-check": "npm exec -- prettier --check .",
                "lint": "npm exec -- eslint . --max-warnings 0",
                "test": "npm exec -- vitest run --coverage",
                "build": "npm run build",
                "coverage-report": "coverage/index.html",
            },
            "pnpm": {
                "setup": "pnpm install --frozen-lockfile",
                "fmt": "pnpm exec prettier --write .",
                "fmt-check": "pnpm exec prettier --check .",
                "lint": "pnpm exec eslint . --max-warnings 0",
                "test": "pnpm exec vitest run --coverage",
                "build": "pnpm build",
                "coverage-report": "coverage/index.html",
            },
        },
        "structure": "src/{app,features,shared}, tests beside code as *.test.js",
    },
    "python": {
        "build": ["uv", "pip"],
        "format": ["ruff format"],
        "lint": ["ruff + mypy", "ruff"],
        "test": ["pytest + pytest-cov"],
        "cmd": {
            "uv": {
                "setup": "uv sync --frozen",
                "fmt": "uv run ruff format .",
                "fmt-check": "uv run ruff format --check .",
                "lint": "uv run ruff check .",
                "typecheck": "uv run mypy src",
                "test": "uv run pytest --cov=src --cov-report=term-missing --cov-report=html",
                "build": "uv build",
                "coverage-report": "htmlcov/index.html",
            },
            "pip": {
                "setup": "python -m pip install -r requirements-dev.txt",
                "fmt": "ruff format .",
                "fmt-check": "ruff format --check .",
                "lint": "ruff check .",
                "typecheck": "mypy src",
                "test": "pytest --cov=src --cov-report=term-missing --cov-report=html",
                "build": "python -m build",
                "coverage-report": "htmlcov/index.html",
            },
        },
        "structure": "src/<package>/{api,domain,infra}, tests/ mirrors src",
    },
    "go": {
        "build": ["go"],
        "format": ["gofmt + goimports"],
        "lint": ["golangci-lint"],
        "test": ["go test + cover"],
        "cmd": {
            "go": {
                "setup": "go mod download",
                "fmt": "gofmt -w . && goimports -w .",
                "fmt-check": 'test -z "$$(gofmt -l .)"',
                "lint": "golangci-lint run",
                "test": "go test ./... -coverprofile=coverage.out",
                "build": "go build ./...",
                "coverage-report": "coverage.out",
            }
        },
        "structure": "cmd/<app>, internal/{api,domain,infra}, tests beside code as *_test.go",
    },
    "dart": {
        "build": ["flutter"],
        "format": ["dart format"],
        "lint": ["flutter analyze (flutter_lints)", "flutter analyze (very_good_analysis)"],
        "test": ["flutter test --coverage"],
        "cmd": {
            "flutter": {
                "setup": "flutter pub get",
                "fmt": "dart format .",
                "fmt-check": "dart format --output=none --set-exit-if-changed .",
                "lint": "flutter analyze --fatal-infos",
                "test": "flutter test --coverage",
                "build": "flutter build apk --debug",
                "coverage-report": "coverage/lcov.info",
            }
        },
        "structure": "lib/{app,features/<name>,shared}, test/ mirrors lib",
    },
    "rust": {
        "build": ["cargo"],
        "format": ["rustfmt"],
        "lint": ["clippy"],
        "test": ["cargo test + cargo-llvm-cov", "cargo test"],
        "cmd": {
            "cargo": {
                "setup": "cargo fetch --locked",
                "fmt": "cargo fmt --all",
                "fmt-check": "cargo fmt --all -- --check",
                "lint": "cargo clippy --workspace --all-targets --locked -- -D warnings",
                "typecheck": "cargo check --workspace --all-targets --locked",
                "test": (
                    "cargo test --workspace --locked && "
                    "cargo llvm-cov --workspace --locked --fail-under-lines {coverage}"
                ),
                "build": "cargo build --workspace --release --locked",
                "coverage-report": "target/llvm-cov/html/index.html (cargo llvm-cov --html)",
            }
        },
        "structure": (
            "Cargo.toml workspace, src/ or crates/<name>/src/, tests/ for integration tests"
        ),
    },
    "c": {
        "build": ["cmake"],
        "format": ["clang-format"],
        "lint": ["clang-tidy"],
        "test": ["ctest + gcovr"],
        "cmd": {
            "cmake": {
                "setup": "cmake --preset dev",
                "fmt": "cmake --build --preset dev --target format",
                "fmt-check": "cmake --build --preset dev --target format-check",
                "lint": "cmake --build --preset dev --target lint",
                "typecheck": "cmake --build --preset dev",
                "test": (
                    "cmake --preset coverage && cmake --build --preset coverage && "
                    "ctest --preset coverage && "
                    "gcovr --root . --filter src/ --filter include/ "
                    "--fail-under-line {coverage} --html-details coverage.html"
                ),
                "build": "cmake --preset release && cmake --build --preset release",
                "coverage-report": "coverage.html",
            }
        },
        "structure": "CMakeLists.txt, CMakePresets.json, src/, include/, tests/",
    },
    "cpp": {"alias": "c"},
    "php": {
        "build": ["composer"],
        "format": ["php-cs-fixer"],
        "lint": ["phpstan"],
        "test": ["phpunit + coverage"],
        "cmd": {
            "composer": {
                "setup": "composer install --no-interaction --prefer-dist",
                "fmt": "vendor/bin/php-cs-fixer fix",
                "fmt-check": "vendor/bin/php-cs-fixer fix --dry-run --diff",
                "lint": "vendor/bin/phpstan analyse --no-progress",
                "test": "composer run test:coverage",
                "build": "composer validate --strict && composer dump-autoload --optimize",
                "coverage-report": "coverage/index.html",
            }
        },
        "structure": "composer.json, src/, tests/, phpunit.xml",
    },
    "ruby": {
        "build": ["bundler"],
        "format": ["rubocop"],
        "lint": ["rubocop"],
        "test": ["rspec + simplecov"],
        "cmd": {
            "bundler": {
                "setup": "bundle install",
                "fmt": "bundle exec rubocop --autocorrect",
                "fmt-check": "bundle exec rubocop --only Layout",
                "lint": "bundle exec rubocop",
                "test": "bundle exec rspec",
                "build": "bundle exec rake build",
                "coverage-report": "coverage/index.html",
            }
        },
        "structure": "Gemfile, lib/<package>/, spec/ mirrors lib",
    },
    "swift": {
        "build": ["swiftpm"],
        "format": ["swift-format"],
        "lint": ["swiftlint"],
        "test": ["swift test + llvm-cov"],
        "cmd": {
            "swiftpm": {
                "setup": "swift package resolve",
                "fmt": "swift format --in-place --recursive Sources Tests",
                "fmt-check": "swift format lint --strict --recursive Sources Tests",
                "lint": "swiftlint lint --strict",
                "typecheck": "swift build --build-tests",
                "test": "swift test --enable-code-coverage && make coverage-check",
                "build": "swift build --configuration release",
                "coverage-report": ".build/debug/codecov/ (coverage-check exports reports)",
            }
        },
        "structure": "Package.swift, Sources/<Target>/, Tests/<Target>Tests/",
    },
    "csharp": {
        "build": ["dotnet"],
        "format": ["dotnet format"],
        "lint": ["roslyn analyzers (warnings as errors)"],
        "test": ["xunit + coverlet"],
        "cmd": {
            "dotnet": {
                "setup": "dotnet restore",
                "fmt": "dotnet format",
                "fmt-check": "dotnet format --verify-no-changes",
                "lint": "dotnet build -warnaserror --no-restore",
                "test": 'dotnet test --collect:"XPlat Code Coverage"',
                "build": "dotnet build -c Release",
                "coverage-report": "TestResults/**/coverage.cobertura.xml",
            }
        },
        "structure": "src/<App>.{Api,Domain,Infrastructure}, tests/<App>.*.Tests",
    },
}
COMMON = {
    "coverage": ["80", "70", "90"],
    "ci": ["github-actions", "gitlab-ci", "none"],
    "hooks": ["pre-commit (fmt-check + lint)", "none"],
    "ai_workflow": ["AGENTS.md", "none"],
}
PRINCIPLES_SOURCE = (
    "https://github.com/multica-ai/andrej-karpathy-skills (CLAUDE.md, guidelines for coding agents)"
)


# Per language: the few rules that differ from the shared rules. Kept short on purpose; a rule a
# formatter or linter already enforces is not repeated here.
CLEAN_CODE: dict[str, list[str]] = {
    "java": [
        "Prefer immutable types (records, final fields); no null returns where Optional fits.",
        "Constructor injection only; no static mutable state.",
        "Throw specific exceptions; never catch Exception to hide a failure.",
    ],
    "kotlin": [
        "Prefer val and immutable collections; avoid !! outside tests.",
        "Model states with sealed types, not flags and nulls.",
        "Keep coroutines structured; never use GlobalScope.",
    ],
    "typescript": [
        "Enable strict mode; no `any`; narrow unknown input at the boundary.",
        "Prefer small pure functions and named exports; no default exports.",
        "Handle every promise; no floating promises.",
    ],
    "javascript": [
        "Use const and let, strict equality, and named exports.",
        "Handle every promise; no floating promises.",
        "Validate input at the boundary; keep functions small and pure where possible.",
    ],
    "python": [
        "Type-annotate public functions; keep modules small with one purpose.",
        "Raise specific exceptions; never use a bare except.",
        "Prefer dataclasses and pure functions; no mutable default arguments.",
    ],
    "go": [
        "Return errors and wrap them with context; no panics for expected failures.",
        "Accept interfaces, return concrete types; keep interfaces small.",
        "Pass context.Context first; no package-level mutable state.",
    ],
    "dart": [
        "Prefer const constructors and immutable models.",
        "Keep widgets small; move logic out of build methods.",
        "Await every Future or mark it unawaited on purpose.",
    ],
    "rust": [
        "Return Result and use `?`; no unwrap or expect outside tests.",
        "Prefer borrowing over cloning; keep unsafe out unless a comment proves it sound.",
        "Derive and implement standard traits instead of ad hoc helpers.",
    ],
    "c": [
        "Check every return value and allocation; free what you allocate in one place.",
        "Keep functions short; no global mutable state.",
        "Compile with warnings as errors.",
    ],
    "php": [
        "Declare strict_types in every file and type every parameter and return.",
        "Constructor injection only; no static helpers with state.",
        "Throw specific exceptions; never suppress errors with @.",
    ],
    "ruby": [
        "Keep methods short and objects single-purpose.",
        "Rescue specific errors only; never a bare rescue.",
        "Prefer plain objects and explicit dependencies over metaprogramming.",
    ],
    "swift": [
        "Prefer structs and let; avoid force unwraps outside tests.",
        "Model failure with throws and Result, not optionals alone.",
        "Keep types small; mark classes final unless designed for subclassing.",
    ],
    "csharp": [
        "Enable nullable reference types and treat warnings as errors.",
        "Constructor injection only; async all the way, no .Result or .Wait().",
        "Throw specific exceptions; never swallow them.",
    ],
}
SHARED_CLEAN_CODE = [
    "Name things for what they mean; a function does one thing and fits on a screen.",
    "No duplicated logic: extract it the second time it is needed, not before.",
    "No dead code, commented-out code or unused dependencies.",
    "Handle errors at the boundary with a clear message; never swallow them.",
    "Comments say why, not what.",
]


def clean_code(language: str) -> list[str]:
    """The language's own rules; a language without an entry has none beyond the shared ones."""
    return CLEAN_CODE.get(language, [])


def language_of(profile: dict[str, Any] | None, layer: str) -> str | None:
    values = ((profile or {}).get("layers") or {}).get(layer) or {}
    lang = str(values.get("language") or "").strip().lower()
    lang = {
        "c#": "csharp",
        "c++": "cpp",
        "golang": "go",
        "js": "javascript",
        "ts": "typescript",
        "c-sharp": "csharp",
    }.get(lang, lang)
    if not lang and values.get("framework") == "flutter":
        lang = "dart"
    entry = CATALOG.get(lang)
    if entry and "alias" in entry:
        return entry["alias"]
    return lang if lang in CATALOG else None


def code_layers(profile: dict[str, Any] | None) -> list[str]:
    return [k for k in ("backend", "frontend", "mobile") if language_of(profile, k)]


def questions(profile: dict[str, Any] | None) -> list[dict[str, Any]]:
    """At most five questions, options first-is-default, prefilled from the stack."""
    out = []
    for layer in code_layers(profile):
        lang = language_of(profile, layer)
        cat = CATALOG[lang]
        build = str(((profile or {}).get("layers") or {}).get(layer, {}).get("build") or "")
        builds = cat["build"] if build not in cat["build"] else [build]
        out.append(
            {
                "key": f"{layer}",
                "q": f"{layer} ({lang}) tooling: build / format / lint / test?",
                "options": [
                    f"{builds[0]} · {cat['format'][0]} · {cat['lint'][0]} · {cat['test'][0]}",
                    *(
                        f"{b} · {f} · {lint} · {cat['test'][0]}"
                        for b, f, lint in zip(
                            cat["build"][1:],
                            cat["format"][1:],
                            cat["lint"][1:],
                            strict=False,
                        )
                    ),
                    "tell me your choice",
                ][:4],
                "default": 0,
            }
        )
    out.append(
        {
            "key": "coverage",
            "q": "Minimum line coverage that fails the build?",
            "options": COMMON["coverage"],
            "default": 0,
        }
    )
    out.append(
        {
            "key": "ci_hooks",
            "q": "CI and local hooks?",
            "options": [
                "github-actions + pre-commit",
                "gitlab-ci + pre-commit",
                "github-actions, no hooks",
                "none",
            ],
            "default": 0,
        }
    )
    out.append(
        {
            "key": "ai_workflow",
            "q": "AI workflow file for coding agents in the repo?",
            "options": COMMON["ai_workflow"],
            "default": 0,
        }
    )
    return out[:5]


def default_tooling(profile: dict[str, Any] | None) -> dict[str, Any]:
    tooling: dict[str, Any] = {"layers": {}}
    for layer in code_layers(profile):
        lang = language_of(profile, layer)
        cat = CATALOG[lang]
        build = str(((profile or {}).get("layers") or {}).get(layer, {}).get("build") or "")
        build = build if build in cat["cmd"] else cat["build"][0]
        tooling["layers"][layer] = {
            "language": lang,
            "build": build,
            "format": cat["format"][0],
            "lint": cat["lint"][0],
            "test": cat["test"][0],
        }
    tooling.update(
        {
            "coverage": 80,
            "ci": "github-actions",
            "hooks": "pre-commit",
            "ai_workflow": "AGENTS.md",
        }
    )
    return tooling


def commands(tooling: dict[str, Any]) -> dict[str, dict[str, str]]:
    out = {}
    for layer, t in (tooling.get("layers") or {}).items():
        cmd = CATALOG[t["language"]]["cmd"].get(t["build"]) or {}
        out[layer] = {
            key: value.replace("{coverage}", str(tooling.get("coverage", 80)))
            for key, value in cmd.items()
        }
    return out


def makefile(tooling: dict[str, Any], name: str) -> str:
    cmds = commands(tooling)
    targets = ["setup", "fmt", "fmt-check", "lint", "typecheck", "test", "build"]
    lines = [
        f"# {name} — one entry point for humans, CI and coding agents.",
        "# `make check` is the gate: it must pass before every commit and in CI.",
        ".PHONY: " + " ".join(targets + ["check", "coverage", "help"]),
        "",
        "help:  ## list targets",
        "\t@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | sed 's/:.*## /\\t/'",
        "",
    ]
    for target in targets:
        steps = []
        for layer, c in cmds.items():
            if target in c:
                folder = "" if len(cmds) == 1 else f"cd {layer} && "
                steps.append(f"\t{folder}{c[target]}")
        lines.append(f"{target}:  ## {target} for every layer")
        lines += steps or ["\t@echo 'nothing to do'"]
        lines.append("")
    lines += [
        "check: fmt-check lint typecheck test  ## the gate: format, lint, types, tests + coverage",
        "",
        "coverage: test  ## open the coverage report paths",
    ]
    for layer, c in cmds.items():
        if c.get("coverage-report"):
            lines.append(f"\t@echo '{layer}: {c['coverage-report']}'")
    if any(t.get("language") == "swift" for t in (tooling.get("layers") or {}).values()):
        lines += [
            "",
            ".PHONY: coverage-check",
            "coverage-check:  ## implement platform-specific llvm-cov export and threshold check",
            "\t@echo 'Configure Swift coverage export and enforce the chosen line floor first.'",
            "\t@exit 1",
        ]
    return "\n".join(lines) + "\n"


def agents_md(
    tooling: dict[str, Any], name: str, stack_lines: dict[str, str], lock: str | None = None
) -> str:
    """Karpathy-style working rules, then this project's gate, layout and coding conventions.

    The four opening sections follow the shape of andrej-karpathy-skills CLAUDE.md, written in
    our words. The specification pointer is the same two lines workspace appends to an existing
    root AGENTS.md. This function does not emit CLAUDE.md.
    """
    from kitlib import workspace

    cov = tooling.get("coverage", 80)
    structure = [
        f"- {layer}: {CATALOG[t['language']]['structure']}"
        for layer, t in (tooling.get("layers") or {}).items()
    ]
    conventions = [f"- {rule}" for rule in SHARED_CLEAN_CODE]
    if len(tooling.get("layers") or {}) == 1:
        conventions += [
            f"- {lang} — {rule}" for lang in languages_of(tooling) for rule in clean_code(lang)
        ]
    elif tooling.get("layers"):
        conventions.append("- Per-language rules live in each layer folder's own AGENTS.md.")
    return "\n".join(
        [
            f"# {name} — instructions for coding agents",
            "",
            "## 1. Think before coding",
            "",
            "State assumptions before writing. When a request has several readings, list them "
            "and ask. When a smaller approach meets the acceptance criteria, name it. "
            "When something is unclear, stop and name what is unclear.",
            "",
            "## 2. Simplicity first",
            "",
            "Write only what the acceptance criteria need. No speculative features, options "
            "or abstractions. No handler for a case that cannot happen.",
            "",
            "## 3. Surgical changes",
            "",
            "Touch only the lines the task needs. Match the existing style. Mention an unrelated "
            "problem instead of fixing it. Remove only what your change made unused.",
            "",
            "## 4. Goal-driven execution",
            "",
            "Turn each task into a test that fails first, make that test pass, then run "
            "`make check`. For several steps, write the plan with a check per step.",
            "",
            f"Principles adapted from {PRINCIPLES_SOURCE}.",
            "",
            (
                f"## Stack (locked {lock}; no framework or library outside it without asking)"
                if lock
                else "## Stack (proposed, not locked yet; ask before adding anything outside it)"
            ),
            *(f"- {k}: {v}" for k, v in stack_lines.items()),
            "",
            "## Commands",
            "- `make setup` — install dependencies from the lockfile",
            "- `make fmt` / `make fmt-check` — format / verify formatting",
            "- `make lint` — static checks, zero warnings",
            "- `make typecheck` — types (where the language has them)",
            f"- `make test` — tests with coverage; below {cov}% line coverage fails",
            "- `make check` — the gate: run it before every commit; CI runs the same",
            "",
            "## Structure",
            *(structure or ["- see the foundation story"]),
            "",
            "## Coding conventions",
            *conventions,
            "",
            "## Definition of done",
            "- Every acceptance criterion the task traces to has a test.",
            f"- `make check` passes; coverage ≥ {cov}%.",
            "- No new dependency outside the locked stack.",
            "- The report names files changed, tests added and AC IDs satisfied.",
            "",
            *workspace.SPEC_POINTER_LINES,
            "",
        ]
    )


# What counts as an existing setup, per concern: any one of these files or folders present.
EXISTING = {
    "gate": ["Makefile", "justfile", "Taskfile.yml"],
    "format": [
        ".prettierrc",
        ".prettierrc.json",
        "prettier.config.js",
        ".clang-format",
        ".editorconfig",
        "rustfmt.toml",
        ".rustfmt.toml",
        ".php-cs-fixer.php",
        ".swift-format",
    ],
    "lint": [
        ".eslintrc",
        ".eslintrc.json",
        "eslint.config.js",
        "eslint.config.mjs",
        ".golangci.yml",
        ".golangci.yaml",
        ".rubocop.yml",
        "ruff.toml",
        ".ruff.toml",
        "checkstyle.xml",
        "detekt.yml",
        ".swiftlint.yml",
        "phpstan.neon",
        ".clang-tidy",
        "analysis_options.yaml",
        "clippy.toml",
    ],
    "tests": ["tests", "test", "spec", "__tests__", "src/test"],
    "ci": [".github/workflows", ".gitlab-ci.yml"],
    "agents": ["AGENTS.md"],
}


def existing_setup(code_root: Path) -> dict[str, list[str]]:
    """Which foundation pieces a code folder already has, so the story only adds what is missing.

    Reads names only, never file contents. A pyproject or package manifest that configures a tool
    is not inspected; the implementing agent reads it before changing anything.
    """
    found: dict[str, list[str]] = {}
    for concern, names in EXISTING.items():
        found[concern] = [n for n in names if (code_root / n).exists()]
    return found


def languages_of(tooling: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for entry in (tooling.get("layers") or {}).values():
        lang = str(entry.get("language") or "")
        if lang and lang not in seen:
            seen.append(lang)
    return seen


def layer_agents_md(tooling: dict[str, Any], layer: str) -> str:
    """The nested file of one layer: only what differs from the root rules, nothing repeated."""
    entry = (tooling.get("layers") or {}).get(layer) or {}
    lang = str(entry.get("language") or "")
    cmds = commands(tooling).get(layer, {})
    cov = tooling.get("coverage", 80)
    return "\n".join(
        [
            f"# {layer} ({lang}) — local rules",
            "",
            "Root AGENTS.md rules apply. This file only adds what is specific to this folder.",
            "",
            "## Commands (run from this folder)",
            *(f"- `{c}`" for c in (cmds.get(t) for t in ("fmt", "lint", "test")) if c),
            f"- Line coverage below {cov}% fails the build.",
            "",
            "## Structure",
            f"- {CATALOG[lang]['structure']}" if lang in CATALOG else "- see the root file",
            "",
            f"## Clean code — {lang}",
            *(f"- {rule}" for rule in clean_code(lang)),
            "",
        ]
    )


def story_sections(tooling: dict[str, Any], bo: str, feat_num: str) -> dict[str, str]:
    """Body sections of the foundation story, AC IDs numbered for the reserved FEAT."""
    cov = int(tooling.get("coverage", 80))
    ci = tooling.get("ci", "github-actions")
    layers = tooling.get("layers") or {}
    names = ", ".join(f"{k} ({v['language']}, {v['build']})" for k, v in layers.items()) or "none"
    n = iter(range(1, 20))

    def ac(title: str, given: str, when: str, then: str) -> str:
        return (
            f"### AC-{feat_num}-{next(n)} — {title}\n\n- **Given** {given}\n- **When** {when}\n"
            f"- **Then** {then}\n"
        )

    acs = [
        ac(
            "Fresh clone sets up in one command",
            "a fresh clone on a machine with the locked runtime versions",
            "a developer runs `make setup`",
            "it exits with code 0 and installs only what the lockfile lists",
        ),
        ac(
            "Formatting is enforced",
            "a source file with one wrongly indented line",
            "`make fmt-check` runs",
            "it exits non-zero and names that file; after `make fmt` it exits 0",
        ),
        ac(
            "Lint fails on a violation",
            "a source file with an unused import",
            "`make lint` runs",
            "it exits non-zero and reports the file and line",
        ),
        ac(
            f"Tests run with a {cov}% coverage floor",
            "the sample module and its test",
            "`make test` runs",
            f"tests pass, a coverage report is written, and line coverage below {cov}% "
            "exits non-zero",
        ),
        ac(
            "One gate for humans, CI and agents",
            "the skeleton project",
            "`make check` runs",
            "it runs fmt-check, lint, typecheck and test in that order and exits 0",
        ),
    ]
    if ci != "none":
        acs.append(
            ac(
                "CI blocks a failing change",
                "a pull request where `make check` fails",
                f"the {ci} pipeline runs",
                "the check is red and the merge is blocked",
            )
        )
    if tooling.get("ai_workflow", "none") != "none":
        acs.append(
            ac(
                "Coding agents get the rules from the repo",
                "a coding agent opens the repository",
                "it reads `AGENTS.md`",
                "it finds the locked stack, the `make` commands, the structure, the working "
                "principles, the definition of done, and a pointer to `.specwright/index.md`",
            )
        )
    acs.append(
        ac(
            "Structure follows the convention",
            "the skeleton project",
            "a developer lists the source folders",
            "they match the structure in `AGENTS.md`, with one sample module and one test",
        )
    )
    return {
        "Goal": (
            "As a developer or coding agent, I want a project skeleton with one verified quality "
            f"gate, so that every later feature starts from the same checks. Business objective: "
            f"{bo}."
        ),
        "Context": (
            f"Layers: {names}. Coverage floor {cov}%. CI: {ci}. Hooks: "
            f"{tooling.get('hooks', 'none')}. Reference files: "
            "`features/FEAT-NNN/foundation/Makefile`, "
            "`features/FEAT-NNN/foundation/AGENTS.md`"
            + ". Tool versions: current stable from official docs, pinned in the lockfiles."
        ),
        "Acceptance criteria": "\n".join(acs),
        "Business rules": (
            f"- BR: line coverage below {cov}% fails `make test`. Example: "
            f"{cov - 0.1:.1f}% fails, {cov:.1f}% passes."
        ),
        "Edge cases and error behavior": (
            "- A missing runtime or wrong major version: `make setup` exits non-zero and names the "
            "required version.\n- No tests found: `make test` exits non-zero."
        ),
        "Non-functional": (
            "- NFR: run time of `make check` on the skeleton ≤ 120 s on a standard CI runner, "
            "measured from the CI job log."
        ),
        "UI/UX": "None — no user interface in the foundation.",
        "Out of scope": (
            "- Deployment and environments — reason: a later story per target.\n"
            "- Feature code — reason: each feature has its own story."
        ),
        "Dependencies and relations": "None — the first story of the codebase.",
        "Open questions": "None",
    }
