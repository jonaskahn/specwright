"""Append-only log of every external write: an intent before the call, a result after it.

An intent line without a matching result means a call may or may not have landed, so the
next run must check the remote state before doing anything else.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


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
