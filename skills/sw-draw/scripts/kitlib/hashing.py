"""Stable content hashes for drafts, plans and original files."""

from __future__ import annotations

import hashlib

from kitlib import frontmatter, markdown

IDENTITY_SECTION = "Identity"


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
