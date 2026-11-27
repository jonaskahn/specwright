# Foundation story (new codebases)

The first story of a new codebase: structure, format, lint, tests with a coverage floor, one
`make check` gate, CI, local hooks and an AI workflow file for coding agents. Every later task
prompt relies on `make check` and `AGENTS.md`.

## When
- New project: no registered code roots (or a repo with no build files yet).
- After the stack step (locked, proposed or skipped). Offer it once; the owner may decline
  (`foundation.py set --decline`; sw-start stops offering it).
- An existing codebase without a gate: offer it as a change ("add `make check`, coverage floor").

## Explore before asking (runtime)
- Read `stack.py show` and `foundation.py questions`; they prefill tool choices per layer.
- When web search is available, check the official docs of each proposed tool for its current
  stable release and recommended setup; mention a notable alternative in one line. Never pin a
  version from memory; the implementing agent pins current versions in the lockfiles.
- Ask the questions in one message (≤ 5, options, defaults). Unanswered → defaults, said so.

## Steps
1. `foundation.py set --defaults`, then `set --layer <l> --build/--format/--lint/--test`,
   `--coverage N`, `--ci`, `--hooks`, `--ai-workflow agents+claude|agents|none` per answer.
   Tooling lives in `stack.yaml` under `tooling`, outside the stack lock hash.
2. Reserve the story with the owner's yes: `record.py accept-split --new-epic "Project
   foundation" --bo BO-NNN --item "Set up project foundation|foundation"` (no BO yet → ask).
3. `new_story.py --reserved FEAT-NNN`, set `links:`, then `foundation.py draft --feat FEAT-NNN`.
   It fills the twelve sections and writes reference files: `02-drafts/foundation/Makefile`,
   `AGENTS.md` and (agents+claude) `CLAUDE.md` with `@AGENTS.md`.
4. Continue as any story: consumer checks, illustration check, hash, card, finish → review.

## Rust tooling

Rust profiles use Cargo, rustfmt and Clippy. Tests run through `cargo test`; the coverage
step uses `cargo-llvm-cov` and enforces the chosen line-coverage floor. The implementing
agent provisions rustfmt, Clippy, llvm-tools-preview and cargo-llvm-cov using reviewed
current tooling versions; generating the foundation story does not install them.
The Cargo workspace must have a committed lockfile before the generated `--locked` checks run.

## Other language presets

| Language | Build | Format / lint | Tests and coverage |
| --- | --- | --- | --- |
| C, C++ | CMake presets | clang-format / clang-tidy | CTest + gcovr |
| PHP | Composer | PHP-CS-Fixer / PHPStan | PHPUnit + configured coverage script |
| Ruby | Bundler | RuboCop | RSpec + SimpleCov |
| Swift | Swift Package Manager | swift format / SwiftLint | swift test + llvm-cov |
| Kotlin | Gradle | Spotless with ktlint / Detekt | JUnit 5 + Kover |
| JavaScript | npm or pnpm | Prettier / ESLint | Vitest + V8 coverage |

Java, TypeScript, Python, Go, Dart/Flutter, Rust and C# retain their presets.
Aliases include C++, cpp, C#, c-sharp, golang, JS and TS (case-insensitive).
JavaScript does not require TypeScript or a tsc check. Kotlin uses Kotlin-specific tasks.

These are foundation contracts, not tool installations or complete build configurations.
The implementing agent creates the referenced configuration before declaring the story done:
- C/C++: dev, coverage and release configure/build presets, coverage test preset, format,
  format-check and lint targets, and compiler coverage instrumentation. gcovr excludes tests.
- PHP: PHPUnit coverage driver and Composer test:coverage script enforcing the chosen floor.
- Ruby: RSpec, SimpleCov started before application code, minimum coverage, and rake build task.
- Kotlin: Spotless, Detekt and Kover plugins with the chosen verification threshold.
- Swift: implement coverage-check to export llvm-cov data for the target platform and enforce
  the chosen floor. The generated target fails explicitly until configured; it never reports
  coverage success without measuring it.
- JavaScript: package build script, formatter/linter configuration and Vitest coverage floor.

Do not pin tool versions from memory. Verify supported releases and setup before implementation.

## What the story guarantees
`make setup | fmt | fmt-check | lint | typecheck | test | build | check`; coverage below the floor
fails; CI runs `make check` and blocks merges; `AGENTS.md` holds the locked stack, commands,
structure, working principles and definition of done; structure follows the stack convention.

## Working principles in AGENTS.md
Written in our words, adapted from multica-ai/andrej-karpathy-skills (CLAUDE.md): think before
coding, least code first, surgical changes, goal-driven verification. Projects may replace the
section with their own rules.
