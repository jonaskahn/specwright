"""Story Markdown conversion. CLI exits 0 on success and 2 on invalid input.

Read conversion returns (Markdown, warnings), so unsupported remote content stays visible.
Output uses LF, a blank line between blocks, and one final newline.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TICK = chr(96)
ALLOWED = {
    "doc",
    "paragraph",
    "heading",
    "bulletList",
    "orderedList",
    "listItem",
    "table",
    "tableRow",
    "tableHeader",
    "tableCell",
    "codeBlock",
    "text",
    "hardBreak",
}
MARKS = {"strong", "em", "code", "link"}


def balanced(text, start, opening, closing):
    depth, i = 1, start + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == opening:
            depth += 1
        elif text[i] == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def inline(text):
    """Scan nested delimiters so link labels can carry their own emphasis."""

    def scan(i, stop="", marks=()):
        out = []

        def emit(value, active=marks):
            if not value:
                return
            node = {"type": "text", "text": value}
            if active:
                node["marks"] = list(active)
            if out and out[-1].get("marks", []) == list(active):
                out[-1]["text"] += value
            else:
                out.append(node)

        while i < len(text):
            if stop and text.startswith(stop, i):
                return out, i + len(stop), True
            char = text[i]
            if char == "\\" and i + 1 < len(text) and text[i + 1] in "\\*_[]()|" + TICK:
                emit(text[i + 1])
                i += 2
                continue
            if char == TICK:
                size = len(text[i:]) - len(text[i:].lstrip(TICK))
                end = text.find(TICK * size, i + size)
                if end >= 0:
                    value = text[i + size: end]
                    if value.startswith(" ") and value.endswith(" ") and value.strip():
                        value = value[1:-1]
                    emit(value, marks + ({"type": "code"},))
                    i = end + size
                    continue
            if char == "[":
                end = balanced(text, i, "[", "]")
                if end >= 0 and text[end + 1: end + 2] == "(":
                    close = balanced(text, end + 1, "(", ")")
                    if close >= 0:
                        link = {
                            "type": "link",
                            "attrs": {
                                "href": text[end + 2: close]
                                .replace(r"\)", ")")
                                .replace(r"\(", "(")
                            },
                        }
                        for node in inline(text[i + 1: end]):
                            node["marks"] = list(marks) + [link] + node.get("marks", [])
                            out.append(node)
                        i = close + 1
                        continue
            delimiter = "**" if text.startswith("**", i) else ("*" if char == "*" else "")
            if delimiter:
                mark = {"type": "strong" if len(delimiter) == 2 else "em"}
                nodes, end, closed = scan(i + len(delimiter), delimiter, marks + (mark,))
                if closed and nodes:
                    out.extend(nodes)
                    i = end
                    continue
            emit(char)
            i += 1
        return out, i, False

    return scan(0)[0]


def paragraph(text):
    content = []
    for i, line in enumerate(text.split("\n")):
        if i:
            content.append({"type": "hardBreak"})
        content.extend(inline(line))
    return {"type": "paragraph", "content": content}


def cells(line):
    """Pipes inside code or escaped pipes belong to the cell, not the table."""
    text = line.strip()
    parts, buf, i, code = [], [], 0, 0
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            buf.append(text[i: i + 2])
            i += 2
            continue
        if char == TICK:
            size = len(text[i:]) - len(text[i:].lstrip(TICK))
            code = size if not code else (0 if code == size else code)
            buf.append(TICK * size)
            i += size
            continue
        if char == "|" and not code:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(char)
        i += 1
    parts.append("".join(buf).strip())
    if text.startswith("|"):
        parts.pop(0)
    if text.endswith("|") and not code and not text.endswith(r"\|"):
        parts.pop()
    return parts


def md_to_adf(md):
    lines = md.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    blocks, i = [], 0
    heading = re.compile(r"^(#{1,6}) (.*)$")
    listing = re.compile(r"^(- |([0-9]+)\. )(.*)$")

    def table_at(index):
        return (
                index + 1 < len(lines)
                and "|" in lines[index]
                and bool(cells(lines[index + 1]))
                and all(re.fullmatch(r":?-{3,}:?", c) for c in cells(lines[index + 1]))
        )

    def special(index):
        return (
                heading.match(lines[index])
                or listing.match(lines[index])
                or lines[index].startswith(TICK * 3)
                or table_at(index)
        )

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        match = heading.match(line)
        if match:
            blocks.append(
                {"type": "heading", "attrs": {"level": len(match[1])}, "content": inline(match[2])}
            )
            i += 1
        elif line.startswith(TICK * 3):
            size = len(line) - len(line.lstrip(TICK))
            language, buf = line[size:].strip(), []
            i += 1
            while i < len(lines) and lines[i] != TICK * size:
                buf.append(lines[i])
                i += 1
            if i == len(lines):
                raise ValueError("unclosed code fence")
            value = "\n".join(buf)
            node = {
                "type": "codeBlock",
                "content": [{"type": "text", "text": value}] if value else [],
            }
            if language:
                node["attrs"] = {"language": language}
            blocks.append(node)
            i += 1
        elif table_at(i):
            rows = [cells(line)]
            i += 2
            while i < len(lines) and lines[i].strip() and "|" in lines[i]:
                rows.append(cells(lines[i]))
                i += 1
            if any(len(r) != len(rows[0]) for r in rows):
                raise ValueError("table rows must have the same width")
            blocks.append(
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {
                                    "type": "tableHeader" if n == 0 else "tableCell",
                                    "content": [paragraph(c)],
                                }
                                for c in row
                            ],
                        }
                        for n, row in enumerate(rows)
                    ],
                }
            )
        elif listing.match(line):
            first = listing.match(line)
            ordered, items = bool(first[2]), []
            while i < len(lines):
                match = listing.match(lines[i])
                if not match or bool(match[2]) != ordered:
                    break
                items.append({"type": "listItem", "content": [paragraph(match[3])]})
                i += 1
            node = {"type": "orderedList" if ordered else "bulletList", "content": items}
            if ordered:
                node["attrs"] = {"order": int(first[2])}
            blocks.append(node)
        else:
            buf = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not special(i):
                buf.append(lines[i])
                i += 1
            blocks.append(paragraph("\n".join(buf)))
    doc = {"version": 1, "type": "doc", "content": blocks}
    validate_adf(doc)
    return doc


def validate_adf(doc):
    children = {
        "doc": {"paragraph", "heading", "bulletList", "orderedList", "table", "codeBlock"},
        "paragraph": {"text", "hardBreak"},
        "heading": {"text", "hardBreak"},
        "bulletList": {"listItem"},
        "orderedList": {"listItem"},
        "listItem": {"paragraph", "bulletList", "orderedList"},
        "table": {"tableRow"},
        "tableRow": {"tableHeader", "tableCell"},
        "tableHeader": {"paragraph"},
        "tableCell": {"paragraph"},
        "codeBlock": {"text"},
        "text": set(),
        "hardBreak": set(),
    }
    if (
            not isinstance(doc, dict)
            or doc.get("type") != "doc"
            or doc.get("version") != 1
            or "content" not in doc
    ):
        raise ValueError("expected a version 1 ADF document")

    def check(node):
        kind = node.get("type")
        if kind not in ALLOWED:
            raise ValueError(f"unsupported ADF output: {kind}")
        if kind == "text" and (not isinstance(node.get("text"), str) or not node["text"]):
            raise ValueError("text must not be empty")
        if kind == "heading" and node.get("attrs", {}).get("level") not in range(1, 7):
            raise ValueError("invalid heading level")
        for mark in node.get("marks", []):
            if kind != "text" or mark.get("type") not in MARKS:
                raise ValueError("invalid mark")
            if mark["type"] == "link" and not isinstance(mark.get("attrs", {}).get("href"), str):
                raise ValueError("link needs href")
        content = node.get("content", [])
        if not isinstance(content, list):
            raise ValueError("content must be an array")
        for child in content:
            if not isinstance(child, dict) or child.get("type") not in children[kind]:
                raise ValueError(f"invalid child in {kind}")
            check(child)

    check(doc)


def adf_to_md(doc):
    warnings = []

    def extracted(node):
        attrs = node.get("attrs", {})
        return (
                node.get("text", "")
                or "".join(extracted(c) for c in node.get("content", []))
                or str(
            attrs.get(
                "text", attrs.get("displayName", attrs.get("shortName", attrs.get("url", "")))
            )
        )
        )

    def unsupported(node):
        kind = node.get("type", "unknown")
        warning = f"unsupported-node:{kind}"
        if warning not in warnings:
            warnings.append(warning)
        return f"<!-- adf:{kind} -->" + extracted(node)

    def inlines(nodes, table=False):
        out, active = [], []

        def closing(mark):
            if mark["type"] == "link":
                href = mark.get("attrs", {}).get("href", "").replace("(", r"\(").replace(")", r"\)")
                return f"]({href})"
            return {"strong": "**", "em": "*"}[mark["type"]]

        for node in nodes + [{"type": "sentinel"}]:
            marks = node.get("marks", [])
            for mark in marks:
                if mark.get("type") not in MARKS:
                    warning = f"unsupported-mark:{mark.get('type', 'unknown')}"
                    if warning not in warnings:
                        warnings.append(warning)
            code = any(m.get("type") == "code" for m in marks)
            marks = [m for m in marks if m.get("type") in MARKS - {"code"}]
            common = 0
            while common < min(len(active), len(marks)) and active[common] == marks[common]:
                common += 1
            out.extend(closing(m) for m in reversed(active[common:]))
            out.extend(
                "[" if m["type"] == "link" else {"strong": "**", "em": "*"}[m["type"]]
                for m in marks[common:]
            )
            active = marks
            kind = node["type"]
            if kind == "text":
                value = node["text"]
                if code:
                    size = max([len(m[0]) for m in re.finditer(TICK + "+", value)] + [0]) + 1
                    pad = (
                        " " if value.startswith((TICK, " ")) or value.endswith((TICK, " ")) else ""
                    )
                    out.append(TICK * size + pad + value + pad + TICK * size)
                else:
                    for char in value:
                        out.append(
                            "\\" + char if char in "\\*" + TICK or (table and char == "|") else char
                        )
            elif kind == "hardBreak":
                out.append("\n")
            elif kind != "sentinel":
                out.append(unsupported(node))
        return "".join(out)

    def block(node, table=False):
        kind, content = node.get("type"), node.get("content", [])
        if kind == "paragraph":
            return inlines(content, table)
        if kind == "heading":
            return "#" * node["attrs"]["level"] + " " + inlines(content)
        if kind in ("bulletList", "orderedList"):
            start = node.get("attrs", {}).get("order", 1)
            return "\n".join(
                (f"{start + i}. " if kind == "orderedList" else "- ")
                + "\n".join(block(c) for c in item.get("content", []))
                for i, item in enumerate(content)
            )
        if kind == "codeBlock":
            value = "".join(c.get("text", "") for c in content)
            fence = TICK * max(
                3, max([len(m[0]) + 1 for m in re.finditer(TICK + "+", value)] + [0])
            )
            return fence + node.get("attrs", {}).get("language", "") + "\n" + value + "\n" + fence
        if kind == "table":
            rows = [
                "| "
                + " | ".join(
                    " ".join(block(c, True) for c in cell.get("content", []))
                    for cell in row.get("content", [])
                )
                + " |"
                for row in content
            ]
            if rows:
                rows.insert(1, "| " + " | ".join("---" for _ in content[0]["content"]) + " |")
            return "\n".join(rows)
        return unsupported(node)

    if doc.get("type") != "doc" or doc.get("version") != 1:
        raise ValueError("expected a version 1 ADF document")
    rendered = []
    previous = None
    for node in doc.get("content", []):
        if rendered:
            rendered.append("\n" if previous == "heading" else "\n\n")
        rendered.append(block(node))
        previous = node.get("type")
    text = "".join(rendered)
    return (text + "\n" if text else ""), warnings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=["to-adf", "to-md"])
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        text = args.file.read_text(encoding="utf-8")
        if args.direction == "to-adf":
            print(json.dumps(md_to_adf(text), ensure_ascii=False))
        else:
            text, warnings = adf_to_md(json.loads(text))
            sys.stdout.write(text)
            for warning in warnings:
                print(warning, file=sys.stderr)
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
