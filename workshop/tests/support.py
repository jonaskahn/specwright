"""Small helpers shared by tests that write item files."""

from pathlib import Path


def put(path: Path, text: str) -> Path:
    """Write a file, creating the item folder it lives in."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
