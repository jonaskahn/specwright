"""Append-only log of every external write: an intent before the call, a result after it.

An intent line without a matching result means a call may or may not have landed, so the
next run must check the remote state before doing anything else.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Only these skills write outside the project; only their lines mean "may not have landed".
REMOTE_SKILLS = frozenset({"sw-publish"})


def utc_stamp(now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    return secrets.token_hex(2)


def _clean(value: object) -> str:
    return " ".join(str(value).replace("|", "/").split())


def _append(path: Path, fields: list[object]) -> None:
    line = " | ".join(_clean(f) for f in fields) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def intent(
    path: str | Path,
    run: str,
    op: int,
    skill: str,
    action: str,
    target: str,
    *detail: object,
    now: datetime | None = None,
) -> None:
    """Record what is about to happen. Call this before the external request is sent."""
    _append(
        Path(path),
        [utc_stamp(now), "INTENT", f"run={run}", f"op={op}", skill, action, target, *detail],
    )


def result(
    path: str | Path,
    run: str,
    op: int,
    outcome: str,
    *detail: object,
    now: datetime | None = None,
) -> None:
    """Record how the operation ended; outcome is 'ok' or 'error'."""
    _append(Path(path), [utc_stamp(now), "RESULT", f"run={run}", f"op={op}", outcome, *detail])


@dataclass
class Entry:
    stamp: str
    kind: str
    run: str
    op: int
    fields: list[str]


def read(path: str | Path) -> list[Entry]:
    target = Path(path)
    if not target.exists():
        return []
    entries = []
    for line in target.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split(" | ")]
        if len(parts) < 4 or parts[1] not in ("INTENT", "RESULT"):
            continue
        if not (parts[2].startswith("run=") and parts[3].startswith("op=")):
            continue
        try:
            op = int(parts[3][3:])
        except ValueError:
            continue
        entries.append(Entry(parts[0], parts[1], parts[2][4:], op, parts[4:]))
    return entries


def unfinished(path: str | Path) -> list[Entry]:
    """Intents that never received a result."""
    entries = read(path)
    done = {(e.run, e.op) for e in entries if e.kind == "RESULT"}
    return [e for e in entries if e.kind == "INTENT" and (e.run, e.op) not in done]


def uncertain(path: str | Path, skills: frozenset[str] = REMOTE_SKILLS) -> list[Entry]:
    """Remote intents with no result, or that ended in error: state that needs recovery."""
    entries = read(path)
    remote = {
        (e.run, e.op)
        for e in entries
        if e.kind == "INTENT" and e.fields[:1] and e.fields[0] in skills
    }
    done = {(e.run, e.op) for e in entries if e.kind == "RESULT"}
    failed = [
        e
        for e in entries
        if e.kind == "RESULT" and (e.run, e.op) in remote and e.fields[:1] == ["error"]
    ]
    return [e for e in entries if e.kind == "INTENT" and (e.run, e.op) in remote - done] + failed


def file_hash(path: Path) -> str:
    """Short content hash for logged files; line-ending changes do not count."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


class Operation:
    """Collects the files one logged operation wrote, so the result can hash them."""

    def __init__(self, log: Path) -> None:
        self.base = log.parent.parent
        self.files: list[Path] = []

    def wrote(self, *paths: Path) -> None:
        self.files.extend(paths)


@contextmanager
def operation(
    path: str | Path,
    skill: str,
    action: str,
    target: str,
    *detail: object,
    now: datetime | None = None,
) -> Iterator[Operation]:
    """Log one local write: an intent first, then a result that is always written.

    Call `op.wrote(file)` for each file written; the result carries `file=<path>@<hash>` so a later
    edit made outside the scripts can be told apart. An exception ends the operation with `error`
    and is re-raised, so an intent never dangles.
    """
    log = Path(path)
    run = new_run_id()
    intent(log, run, 1, skill, action, target, *detail, now=now)
    op = Operation(log)
    try:
        yield op
    except BaseException as exc:
        result(log, run, 1, "error", type(exc).__name__, str(exc), now=now)
        raise
    written = []
    for file in dict.fromkeys(op.files):
        if file.is_file():
            rel = (
                file.relative_to(op.base).as_posix() if file.is_relative_to(op.base) else file.name
            )
            written.append(f"file={rel}@{file_hash(file)}")
    result(log, run, 1, "ok", *written, now=now)


def drift(path: str | Path) -> list[str]:
    """Logged files whose content changed after their last logged write (or that vanished).

    Only files that a logged operation wrote are judged; everything else is unknown, not drift.
    """
    log = Path(path)
    base = log.parent.parent
    last: dict[str, str] = {}
    for entry in read(log):
        if entry.kind != "RESULT" or entry.fields[:1] != ["ok"]:
            continue
        for item in entry.fields[1:]:
            if item.startswith("file=") and "@" in item:
                name, digest = item[5:].rsplit("@", 1)
                last[name] = digest
    found = []
    for name, digest in sorted(last.items()):
        target = base / name
        if not target.is_file():
            found.append(f"{name} is gone since its last logged write")
        elif file_hash(target) != digest:
            found.append(f"{name} changed outside a logged write")
    return found
