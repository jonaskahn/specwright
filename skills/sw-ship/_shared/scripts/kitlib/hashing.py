"""Stable content hashes for drafts, plans and original files."""

from __future__ import annotations

import hashlib
import re

from kitlib import frontmatter, markdown

IDENTITY_SECTION = "Identity"
_DRAFT_HASH = re.compile(r"Draft hash:\s*\S+")


def bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_hash(text: str) -> str:
    return "sha256:" + bytes_hash(text.encode("utf-8"))


def body_hash(body: str) -> str:
    """Hash a Markdown body without its Identity section, ignoring whitespace noise.

    The Identity block carries the hash itself, so it is excluded to keep the value stable.
    """
    cleaned = markdown.normalise(markdown.drop_section(body, IDENTITY_SECTION))
    return text_hash(cleaned + "\n")


def draft_hash(text: str) -> str:
    """Hash of a draft file; front matter changes such as status do not affect it."""
    return body_hash(frontmatter.parse(text).body)


def short(value: str, length: int = 12) -> str:
    """First characters of the hex digest, without the 'sha256:' prefix."""
    return value.removeprefix("sha256:")[:length]


def _recorded_line(text: str) -> str:
    match = _DRAFT_HASH.search(text)
    if not match:
        return ""
    return match.group(0).split(":", 1)[1].strip()


def stamp(text: str) -> str:
    """Record the draft hash in front matter, and on a legacy Identity line when one remains.

    Front matter is excluded from the hash, and so is the Identity section, so the result
    hashes to itself. Removing the DoR section does change the hash; stamp again after that.
    """
    digest = draft_hash(text)
    text = _DRAFT_HASH.sub("Draft hash: " + digest, text)
    if frontmatter.parse(text).fm is None:
        return text
    return frontmatter.update(text, {"draft_hash": digest})


def needs_stamp(text: str) -> bool:
    """True when the recorded draft hash differs from the current draft hash."""
    digest = draft_hash(text)
    recorded = str((frontmatter.parse(text).fm or {}).get("draft_hash") or "")
    if recorded:
        return recorded != digest
    line = _recorded_line(text)
    if not line:
        return False
    return line != digest
