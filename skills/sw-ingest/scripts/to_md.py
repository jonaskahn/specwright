#!/usr/bin/env python3
"""Preserve original bytes and produce a source snapshot, not an interpretation.

Exit codes: 0 converted or duplicate, 2 invalid input/I/O/converter failure,
3 refused unsafe input or missing consent, 4 degraded snapshot written.
Stdout contains JSON; stderr contains value-free diagnostics.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

from secrets_scan import scan  # noqa: E402

from kitlib import frontmatter, fsio, hashing, ids, schema, tables, workspace  # noqa: E402

MAX_BYTES = 50 * 1024 * 1024
MAX_PAGES = 300
HIDDEN = re.compile("[\u00ad\u061c\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
INJECTION = re.compile(
    r"ignore (?:all |the )?(?:previous|prior) instructions|system prompt|run (?:this |the )?command"
    r"|call (?:the )?tool|notes? to (?:the )?ai|you are now",
    re.I,
)


class Refused(ValueError):
    pass


class MissingTool(ValueError):
    pass


def run(argv: list[str]) -> str:
    tool = shutil.which(argv[0])
    if not tool:
        raise MissingTool(argv[0])
    result = subprocess.run([tool, *argv[1:]], capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise ValueError("converter failed")
    return result.stdout.decode("utf-8", errors="replace")


def version(tool: str) -> str:
    try:
        text = run([tool, "--version"]).splitlines()
        return tool + " " + (text[0][:160] if text else "version-unknown")
    except (ValueError, OSError, subprocess.TimeoutExpired):
        return tool + " version-unknown"


class HTMLText(HTMLParser):
    """Suppress active markup because scripts and styles are not business prose."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(text: str) -> str:
    parser = HTMLText()
    parser.feed(text)
    return "".join(parser.parts)


def adf_to_md(node, warnings: list[str]) -> str:
    """Retain unknown-node text and flag loss rather than silently dropping evidence."""
    if not isinstance(node, dict):
        return ""
    kind = node.get("type", "unknown")
    children = "".join(adf_to_md(n, warnings) for n in node.get("content", []))
    attrs = node.get("attrs", {})
    if kind == "text":
        value = node.get("text", "")
        for mark in node.get("marks", []):
            name = mark.get("type")
            wrap = {"strong": "**", "em": "*", "code": "\x60", "strike": "~~"}.get(name)
            if wrap:
                value = wrap + value + wrap
            elif name == "link":
                value = "[" + value + "](" + mark.get("attrs", {}).get("href", "") + ")"
            else:
                warnings.append("unsupported-mark:" + str(name))
        return value
    if kind == "hardBreak":
        return "\n"
    if kind == "heading":
        return "#" * max(1, min(6, int(attrs.get("level", 1)))) + " " + children + "\n\n"
    if kind == "listItem":
        return "- " + children.strip() + "\n"
    if kind == "codeBlock":
        return "~~~\n" + children + "\n~~~\n\n"
    if kind == "blockquote":
        return "\n".join("> " + line for line in children.splitlines()) + "\n\n"
    if kind == "rule":
        return "\n---\n"
    if kind in {"tableCell", "tableHeader"}:
        return " " + children.strip().replace("|", "\\|") + " |"
    if kind == "tableRow":
        return "|" + children + "\n"
    if kind in {"paragraph", "bulletList", "orderedList", "table"}:
        if kind in {"orderedList", "table"}:
            warnings.append("layout-lost")
        return children + "\n\n"
    if kind == "doc":
        return children
    warnings.append("unsupported-node:" + str(kind))
    return children or "[unsupported-node:" + str(kind) + "]"


def ocr(path: Path, pages: int, locale: str) -> tuple[str, str]:
    language = "vie+eng" if locale.startswith("vi") else "eng"
    if path.suffix.lower() != ".pdf":
        return run(["tesseract", str(path), "stdout", "-l", language, "--psm", "6"]), version(
            "tesseract"
        )
    with tempfile.TemporaryDirectory() as folder:
        prefix = str(Path(folder) / "page")
        run(["pdftoppm", "-r", "300", "-f", "1", "-l", str(pages), "-png", str(path), prefix])
        images = sorted(Path(folder).glob("page-*.png"))
        if not images or len(images) > MAX_PAGES:
            raise ValueError("OCR pages unavailable")
        text = "\n\n".join(
            run(["tesseract", str(p), "stdout", "-l", language, "--psm", "6"]) for p in images
        )
        return text, version("pdftoppm") + "; " + version("tesseract")


def convert(
        path: Path, data: bytes, locale: str = "en"
) -> tuple[str, str, str, list[str], bool, str]:
    ext = path.suffix.lower()
    warnings: list[str] = []
    kind, source_version = "other", "UNKNOWN"
    native = "specwright-native 0.1.0"
    text = ""
    converter = native
    try:
        if ext in {".md", ".txt"}:
            text = data.decode("utf-8-sig")
        elif ext == ".csv":
            rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
            text = "\n".join(
                "| "
                + " | ".join(cell.replace("|", "\\|").replace("\n", "<br>") for cell in row)
                + " |"
                for row in rows
            )
            if rows:
                lines = text.splitlines()
                lines.insert(1, "| " + " | ".join("---" for _ in rows[0]) + " |")
                text = "\n".join(lines)
        elif ext in {".html", ".htm"}:
            kind = "html"
            text = html_text(data.decode("utf-8-sig"))
            warnings.append("layout-lost")
        elif ext == ".eml":
            kind = "email"
            message = BytesParser(policy=policy.default).parsebytes(data)
            body = message.get_body(preferencelist=("plain", "html"))
            text = (
                    "\n".join(
                        f"{key}: {message.get(key, 'UNKNOWN')}"
                        for key in ("Subject", "From", "To", "Date")
                    )
                    + "\n\n"
            )
            if body:
                content = body.get_content()
                text += html_text(content) if body.get_content_subtype() == "html" else content
            warnings.append("attachments-not-extracted")
        elif ext == ".json":
            issue = json.loads(data)
            if (
                    not isinstance(issue, dict)
                    or not isinstance(issue.get("fields"), dict)
                    or "key" not in issue
            ):
                raise ValueError("not Jira issue JSON")
            kind = "jira-issue"
            fields = issue["fields"]
            source_version = "updated=" + str(fields.get("updated", "UNKNOWN"))
            description = fields.get("description")
            text = "# " + str(issue["key"]) + ": " + str(fields.get("summary", "UNKNOWN")) + "\n\n"
            text += (
                adf_to_md(description, warnings)
                if isinstance(description, dict)
                else str(description or "")
            )
            converter = "specwright-adf 0.1.0"
        elif ext == ".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                members = archive.infolist()
                if any(m.flag_bits & 1 for m in members):
                    raise Refused("password-protected archive")
                text = "# Archive members (not extracted)\n\n" + "\n".join(
                    "> " + json.dumps(m.filename, ensure_ascii=False) for m in members
                )
            warnings.append("archive-list-only")
        elif ext == ".pdf":
            kind = "pdf"
            if re.search(rb"/Encrypt\b", data):
                raise Refused("password-protected PDF")
            # pdfinfo understands compressed page trees; a byte regex cannot enforce the cap.
            info = run(["pdfinfo", str(path)])
            if re.search(r"Encrypted:\s+yes", info, re.I):
                raise Refused("password-protected PDF")
            match = re.search(r"Pages:\s+(\d+)", info)
            if not match:
                raise Refused("cannot verify PDF page count")
            pages = int(match.group(1))
            if not 1 <= pages <= MAX_PAGES:
                raise Refused("PDF page limit exceeded")
            fonts = run(["pdffonts", str(path)]).splitlines()[2:]
            if any(line.strip() for line in fonts):
                text = run(["pdftotext", "-layout", str(path), "-"])
                converter = version("pdftotext")
            if sum(c.isprintable() and not c.isspace() for c in text) < 20 * pages:
                warnings.extend(["low-text-quality", "layout-lost", "needs-visual-review"])
                text, converter = ocr(path, pages, locale)
        elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            kind = "image"
            warnings.extend(["layout-lost", "needs-visual-review"])
            if ext in {".tif", ".tiff"}:
                raise MissingTool("multipage-image-check-unavailable")
            text, converter = ocr(path, 1, locale)
        elif ext in {".docx", ".odt", ".epub", ".rtf", ".xlsx", ".pptx"}:
            kind = {".docx": "docx", ".xlsx": "xlsx"}.get(ext, "other")
            if zipfile.is_zipfile(io.BytesIO(data)):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if any(m.flag_bits & 1 for m in archive.infolist()):
                        raise Refused("password-protected document")
            elif ext != ".rtf":
                raise Refused("encrypted or invalid document container")
            tool = "pandoc" if ext in {".docx", ".odt", ".epub", ".rtf"} else "markitdown"
            text = run([tool, str(path), "-t", "gfm"] if tool == "pandoc" else [tool, str(path)])
            converter = version(tool)
        elif ext in {".doc", ".xls", ".ppt"}:
            # Opaque binary formats cannot be proven macro-free with the standard library.
            raise MissingTool("legacy-conversion-requires-reviewed-macro-free-export")
        else:
            raise MissingTool("unsupported-format")
    except MissingTool as exc:
        warnings.append("converter-unavailable:" + str(exc))
        return text, kind, converter, warnings, True, source_version
    if sum(c.isprintable() and not c.isspace() for c in text) < 20:
        warnings.append("low-text-quality")
    return text, kind, converter, warnings, False, source_version


def clean(text: str, warnings: list[str]) -> str:
    if HIDDEN.search(text):
        warnings.append("hidden-chars")
    text = unicodedata.normalize("NFC", HIDDEN.sub("", text))
    if INJECTION.search(text):
        warnings.append("possible-injection")
        text = "\n".join("> " + line for line in text.splitlines())
    if "\ufffd" in text:
        warnings.append("decode-replacement")
    return text


def ingest(
        path: Path,
        out: Path,
        *,
        scope: str | None = None,
        source: str | None = None,
        source_version: str | None = None,
        locale: str = "en",
        retain_sensitive_raw: bool = False,
) -> dict:
    path, out = path.resolve(), out.resolve()
    if out.name != "00-inbox":
        raise ValueError("output must be the resolved project's 00-inbox directory")
    if path.stat().st_size > MAX_BYTES:
        raise Refused("input exceeds 50 MB")
    with path.open("rb") as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise Refused("input exceeds 50 MB")
    digest = hashing.bytes_hash(data)
    root = out.parent
    registry_path = root / "_meta" / "id-registry.md"
    registry = tables.parse(
        registry_path.read_text(encoding="utf-8") if registry_path.exists() else "# ID registry\n\n"
    )
    if registry.table is None:
        registry.table = tables.Table(list(schema.REGISTRY_COLUMNS))
    for column in ("Kind", "Last snapshot", "State"):
        registry.table.col(column)
    taken = [str(ref) for ref in ids.find_refs(registry.render())]
    for snapshot in sorted(out.glob("SRC-*.md")):
        taken.append(snapshot.stem)
        parsed = frontmatter.parse(snapshot.read_text(encoding="utf-8"))
        if parsed.fm and parsed.fm.get("sha256") == digest:
            return {"duplicate": True, "id": parsed.fm.get("id"), "sha256": digest}
    for raw in (out / "raw").glob(digest[:12] + "-*"):
        if hashing.bytes_hash(raw.read_bytes()) == digest:
            return {"duplicate": True, "raw": str(raw), "sha256": digest}
    text, kind, converter, warnings, degraded, inferred_version = convert(path, data, locale)
    text = clean(text, warnings)
    findings = scan(text)
    if findings and not retain_sensitive_raw:
        raise Refused(
            "sensitive material requires explicit raw-retention consent; "
            "scan or redact a local copy first"
        )
    if findings:
        warnings.append("sensitive-content")
    number = ids.next_id("SRC", taken, width=4)
    fm = {
        "id": number,
        "type": "snapshot",
        "source_kind": kind,
        "source": source or path.as_uri(),
        "source_version": source_version or inferred_version,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sha256": digest,
        "converter": converter,
        "status": "raw",
        "warnings": sorted(set(warnings)),
        "degraded": degraded,
    }
    if scope:
        fm["scope"] = scope
    rendered = frontmatter.render(fm, "\n" + text.rstrip() + "\n")
    raw_path = out / "raw" / (digest[:12] + "-" + path.name)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation keeps originals append-only, including on a prefix collision.
    with raw_path.open("xb") as handle:
        handle.write(data)
    fsio.atomic_write(out / (number + ".md"), rendered)
    key = ids.qualify(scope, number) if scope else number
    registry.table.upsert(
        key, {"Kind": "snapshot", "Last snapshot": "00-inbox/" + number + ".md", "State": "raw"}
    )
    fsio.atomic_write(registry_path, registry.render())
    return {
        "id": number,
        "sha256": digest,
        "duplicate": False,
        "degraded": degraded,
        "warnings": fm["warnings"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument(
        "--out", type=Path, required=True, help="resolved project 00-inbox directory"
    )
    parser.add_argument("--scope")
    parser.add_argument("--source")
    parser.add_argument("--source-version")
    parser.add_argument("--locale", default="en")
    parser.add_argument(
        "--retain-sensitive-raw",
        action="store_true",
        help="explicit consent to keep sensitive originals locally",
    )
    args = parser.parse_args(argv)
    try:
        root = workspace.find_root(args.out.parent.resolve())
        if root:
            selected = workspace.resolve(
                root, arg=args.scope, cwd=args.out.parent.resolve(), write=True
            )
            if workspace.scope_dir(root, selected).resolve() != args.out.parent.resolve():
                raise Refused("output does not match selected scope")
            args.scope = selected
        result = ingest(
            args.file,
            args.out,
            scope=args.scope,
            source=args.source,
            source_version=args.source_version,
            locale=args.locale,
            retain_sensitive_raw=args.retain_sensitive_raw,
        )
        print(json.dumps(result))
        if result.get("warnings"):
            print("warning: " + ", ".join(result["warnings"]), file=sys.stderr)
        return 4 if result.get("degraded") else 0
    except (Refused, workspace.AskUser) as exc:
        print("refused: " + str(exc), file=sys.stderr)
        return 3
    except (
            TypeError,
            RecursionError,
            ValueError,
            OSError,
            subprocess.TimeoutExpired,
            zipfile.BadZipFile,
            workspace.WorkspaceError,
    ):
        print(
            "error: unreadable input, invalid metadata or converter failure; "
            "no converted text fabricated",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
