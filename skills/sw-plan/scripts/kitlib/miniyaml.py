"""Small YAML subset reader and writer for front matter and manifests.

Supported: nested maps, block lists of scalars or maps, flow lists of scalars, quoted and
plain scalars, booleans, null, integers and comments. Anything else (anchors, multi-line
scalars, nested flow collections, tab indentation) is rejected with a line number so that
a document never silently means something different in a full YAML parser.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from typing import Any


class YamlError(ValueError):
    """Raised when a document uses syntax outside the supported subset."""

    def __init__(self, message: str, line: int = 0) -> None:
        super().__init__(f"line {line}: {message}" if line else message)
        self.line = line


_INT = re.compile(r"^-?(0|[1-9]\d*)$")
_KEY = re.compile(r"^([A-Za-z_][\w.\-]*)\s*:(?:\s+(.*))?$")
_KEYWORDS = {"true": True, "false": False, "null": None, "~": None}


def _strip_comment(text: str) -> str:
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 2
                continue
            if ch == "'" and quote == "'" and text[i + 1 : i + 2] == "'":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'" and (i == 0 or text[i - 1] in " [,:{"):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
        i += 1
    return text.rstrip()


def _unquote(token: str, line: int) -> str:
    if token[0] == '"':
        try:
            value = json.loads(token)
        except json.JSONDecodeError as exc:
            raise YamlError(f"invalid double-quoted string: {exc.msg}", line) from exc
        return value
    if len(token) < 2 or token[-1] != "'":
        raise YamlError("unterminated single-quoted string", line)
    return token[1:-1].replace("''", "'")


def _split_flow(inner: str, line: int) -> list[str]:
    items: list[str] = []
    buf: list[str] = []
    quote = None
    i = 0
    while i < len(inner):
        ch = inner[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(inner):
                buf.append(inner[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'" and not "".join(buf).strip():
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        elif ch in "[]{}":
            raise YamlError("nested flow collections are not supported", line)
        else:
            buf.append(ch)
        i += 1
    if quote:
        raise YamlError("unterminated quote in flow list", line)
    items.append("".join(buf))
    return items


def parse_scalar(token: str, line: int = 0) -> Any:
    token = token.strip()
    if token == "":
        return None
    first = token[0]
    if first in "\"'":
        return _unquote(token, line)
    if first == "[":
        if not token.endswith("]"):
            raise YamlError("unterminated flow list", line)
        inner = token[1:-1].strip()
        if not inner:
            return []
        parts = _split_flow(inner, line)
        if any(not p.strip() for p in parts):
            raise YamlError("empty item in flow list", line)
        return [parse_scalar(p, line) for p in parts]
    if first == "{":
        if token == "{}":
            return {}
        raise YamlError("flow maps are not supported", line)
    if first in "&*!|>%@`":
        raise YamlError(f"unsupported syntax starting with '{first}'; quote the value", line)
    if token in _KEYWORDS:
        return _KEYWORDS[token]
    if _INT.match(token):
        return int(token)
    return token


def _tokenise(text: str) -> list[tuple[int, str, int]]:
    out = []
    for number, raw in enumerate(text.splitlines(), 1):
        lead = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in lead:
            raise YamlError("tab used for indentation", number)
        stripped = _strip_comment(raw)
        if not stripped.strip():
            continue
        out.append((len(stripped) - len(stripped.lstrip(" ")), stripped.strip(), number))
    return out


def _is_item(text: str) -> bool:
    return text == "-" or text.startswith("- ")


class _Parser:
    def __init__(self, lines: list[tuple[int, str, int]]) -> None:
        self.lines = lines
        self.pos = 0

    def parse(self) -> Any:
        if not self.lines:
            return {}
        value = self.block(self.lines[0][0])
        if self.pos < len(self.lines):
            raise YamlError("unexpected indentation", self.lines[self.pos][2])
        return value

    def block(self, indent: int) -> Any:
        return self.seq(indent) if _is_item(self.lines[self.pos][1]) else self.map(indent)

    def seq(self, indent: int) -> list[Any]:
        out: list[Any] = []
        while self.pos < len(self.lines):
            ind, text, number = self.lines[self.pos]
            if ind < indent or not _is_item(text):
                break
            if ind > indent:
                raise YamlError("unexpected indentation", number)
            rest = text[1:].strip()
            if not rest:
                self.pos += 1
                nxt = self.lines[self.pos] if self.pos < len(self.lines) else None
                out.append(self.block(nxt[0]) if nxt and nxt[0] > indent else None)
            elif _is_item(rest):
                raise YamlError("nested lists are not supported", number)
            elif _KEY.match(rest):
                offset = indent + len(text) - len(text[1:].lstrip())
                self.lines[self.pos] = (offset, rest, number)
                out.append(self.map(offset))
            else:
                out.append(parse_scalar(rest, number))
                self.pos += 1
        return out

    def map(self, indent: int) -> dict[str, Any]:
        out: dict[str, Any] = {}
        while self.pos < len(self.lines):
            ind, text, number = self.lines[self.pos]
            if ind < indent or _is_item(text):
                break
            if ind > indent:
                raise YamlError("unexpected indentation", number)
            match = _KEY.match(text)
            if not match:
                raise YamlError("expected 'key: value'", number)
            key, rest = match.group(1), match.group(2) or ""
            if key in out:
                raise YamlError(f"duplicate key '{key}'", number)
            self.pos += 1
            if rest:
                out[key] = parse_scalar(rest, number)
                continue
            nxt = self.lines[self.pos] if self.pos < len(self.lines) else None
            if nxt and nxt[0] > indent:
                out[key] = self.block(nxt[0])
            elif nxt and nxt[0] == indent and _is_item(nxt[1]):
                out[key] = self.seq(indent)
            else:
                out[key] = None
        return out


def loads(text: str) -> dict[str, Any]:
    """Parse a document made of a top-level map."""
    value = _Parser(_tokenise(text)).parse()
    if not isinstance(value, dict):
        raise YamlError("top level must be a map")
    return value


_KEY_OK = re.compile(r"^[A-Za-z_][\w.\-]*$")
_FLOW_LIMIT = 88


def _needs_quote(text: str, flow: bool) -> bool:
    if text == "" or text != text.strip():
        return True
    if text in _KEYWORDS or _INT.match(text):
        return True
    if text[0] in "\"'[]{}&*!|>%@`#?:,-" and (text[0] != "-" or text.startswith("- ")):
        return True
    if text.startswith("-") and _INT.match(text):
        return True
    if ": " in text or " #" in text or text.endswith(":") or "\n" in text or "\t" in text:
        return True
    return flow and any(ch in text for ch in ",[]{}")


def _scalar(value: Any, flow: bool = False) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    return json.dumps(text, ensure_ascii=False) if _needs_quote(text, flow) else text


def _inline(value: Any) -> str:
    if isinstance(value, dict):
        if value:
            raise TypeError("non-empty map cannot be written inline")
        return "{}"
    if isinstance(value, list):
        return "[" + ", ".join(_scalar(x, flow=True) for x in value) + "]"
    return _scalar(value)


def _flow_ok(items: list[Any]) -> bool:
    if any(isinstance(x, (dict, list)) for x in items):
        return False
    return len(_inline(items)) <= _FLOW_LIMIT


def _dump_map(data: dict[str, Any], indent: int) -> Iterator[str]:
    pad = " " * indent
    for key, value in data.items():
        if not isinstance(key, str) or not _KEY_OK.match(key):
            raise TypeError(f"unsupported key: {key!r}")
        prefix = f"{pad}{key}:"
        if isinstance(value, dict) and value:
            yield prefix + "\n"
            yield from _dump_map(value, indent + 2)
        elif isinstance(value, list) and value and not _flow_ok(value):
            yield prefix + "\n"
            yield from _dump_seq(value, indent + 2)
        else:
            yield f"{prefix} {_inline(value)}\n"


def _dump_seq(items: list[Any], indent: int) -> Iterator[str]:
    pad = " " * indent
    for item in items:
        if isinstance(item, dict) and item:
            sub = list(_dump_map(item, indent + 2))
            sub[0] = f"{pad}- {sub[0][indent + 2 :]}"
            yield from sub
        elif isinstance(item, list):
            raise TypeError("nested lists are not supported")
        else:
            yield f"{pad}- {_inline(item)}\n"


def dumps(data: dict[str, Any]) -> str:
    """Serialise a map to the supported subset; loads(dumps(x)) == x."""
    if not isinstance(data, dict):
        raise TypeError("top level must be a map")
    return "".join(_dump_map(data, 0))
