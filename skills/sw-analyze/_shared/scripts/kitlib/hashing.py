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


def stamp(text: str) -> str:
    """Restamp the `Draft hash:` line in the Identity section after a body edit.

    Identity is excluded from the hash, so the result hashes to itself: the operation is
    idempotent and a second stamp never changes the value.
    """
    return _DRAFT_HASH.sub("Draft hash: " + draft_hash(text), text)


def needs_stamp(text: str) -> bool:
    """True when the recorded Draft hash differs from the current draft hash."""
    match = _DRAFT_HASH.search(text)
    if not match:
        return False
    recorded = match.group(0).split(":", 1)[1].strip()
    return recorded != draft_hash(text)
