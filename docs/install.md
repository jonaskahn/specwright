# Install and package

## Project installation

Use Python 3.10 or newer. No runtime dependency installation is needed.

```sh
python3 tools/install.py --target /absolute/path/to/spec-repo
```

The installer creates `.agents/skills/sw-*` with the library already vendored,
and `.claude/skills/sw-*` as relative symlinks on macOS/Linux or copies on Windows.
Use `--copy-mirror` to copy on any platform. Codex, Copilot, Cursor and Gemini can
discover the canonical project skills; Claude Code uses its mirror. Agent versions
vary, so verify discovery in the client before depending on automatic selection.

New projects receive AGENTS.md, equal CLAUDE.md and GEMINI.md copies, and a Copilot
instruction pointer. Existing instructions are preserved. If a project already has
instructions, merge the Specwright standing rules manually rather than replacing them.
Any same-name skill collision stops installation before skill files are written.
To upgrade, back up the existing installation and remove only its `sw-*` folders
before reinstalling. Do not install duplicate names at user scope.

Then initialize a workspace:

```sh
python3 /absolute/path/to/spec-repo/.agents/skills/sw-init/scripts/workspace.py init \
  --root /absolute/path/to/spec-repo --mode flat --scope REF --name Refunds \
  --jira-site https://example.atlassian.net --project-key PROJ
```

## Standalone skill archives

```sh
python3 tools/package.py --zip --out dist
```

Each zip contains one skill folder, MIT LICENSE and a private `scripts/kitlib`.
Release output is excluded from version control. Existing output is never replaced;
choose a fresh `--out` directory for another build. Shared templates belong in skill
assets when a script needs them after installation.

## Optional converters

Plain text, Markdown, CSV, email and simple HTML are handled locally. For richer
documents install pandoc, Poppler tools, Tesseract, markitdown or LibreOffice as needed.
No converter is bundled. Missing tools produce explicit degraded results, not invented
document text. Review OCR output against the original, especially amounts and dates.

Run `python3 tools/validate.py` and the unit suite before packaging. Opening a skill
in an agent and checking its selection remains a manual compatibility check.
