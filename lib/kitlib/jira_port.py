"""Safety boundary for ordered Jira writes, independent of transport.

Operation payloads use keyword arguments of the matching Port method. Create payloads
carry fields; edits carry key and fields; attachments carry key and path. Every edit
requires expect_updated. A Plan hash includes the entire ordered operation list.
CLI exits: 0 valid plan, 2 invalid input. Applying is deliberately an import-only API.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
        sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
        break
from kitlib import hashing, writelog  # noqa: E402


class JiraError(Exception):
    """Remote failure with a safe, credential-free diagnostic."""


class NotFound(JiraError):
    pass


class PermissionDenied(JiraError):
    pass


class RateLimited(JiraError):
    def __init__(self, retry_after=1):
        self.retry_after = max(0.0, float(retry_after))
        super().__init__("rate limited")


class Timeout(JiraError):
    def __init__(self, message="request timed out", ambiguous=True):
        self.ambiguous = ambiguous
        super().__init__(message)


class Conflict(JiraError):
    pass


@dataclass(frozen=True)
class Operation:
    kind: str
    payload: dict[str, Any]
    expect_updated: str | None = None
    idempotency_note: str = ""

    def __post_init__(self):
        if self.kind not in {"create", "edit", "link", "attach", "set_property"}:
            raise ValueError(f"unknown operation kind: {self.kind}")
        if not isinstance(self.payload, dict):
            raise ValueError("payload must be an object")
        if self.kind == "edit" and not self.expect_updated:
            raise ValueError("edit needs expect_updated")


def canonical_hash(value):
    return hashing.bytes_hash(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    )


@dataclass
class Plan:
    operations: list[Operation]
    plan_hash: str = ""

    def __post_init__(self):
        self.operations = list(self.operations)
        digest = canonical_hash([asdict(op) for op in self.operations])
        if self.plan_hash and self.plan_hash != digest:
            raise ValueError("plan hash does not match operations")
        self.plan_hash = digest

    @property
    def short_hash(self):
        return self.plan_hash[:8]


class Port(ABC):
    @abstractmethod
    def get_issue(self, key):
        raise NotImplementedError

    @abstractmethod
    def search_by_label(self, project, label):
        raise NotImplementedError

    @abstractmethod
    def list_changelog(self, key):
        raise NotImplementedError

    @abstractmethod
    def list_comments(self, key):
        raise NotImplementedError

    @abstractmethod
    def create_issue(self, fields):
        raise NotImplementedError

    @abstractmethod
    def edit_issue(self, key, fields):
        raise NotImplementedError

    @abstractmethod
    def add_link(self, payload):
        raise NotImplementedError

    @abstractmethod
    def attach_file(self, key, path):
        raise NotImplementedError

    @abstractmethod
    def set_property(self, key, property_key, value):
        raise NotImplementedError

    @abstractmethod
    def get_property(self, key, property_key):
        raise NotImplementedError


@dataclass
class Outcome:
    status: str
    completed: int = 0
    results: list[Any] = field(default_factory=list)
    failed_index: int | None = None
    error: str | None = None
    recovered: bool = False
    recovery_matches: list[dict] = field(default_factory=list)

    @property
    def ok(self):
        return self.status == "ok"


def apply_plan(
    port, plan, writelog_path, run_id, scope_id, *, sleep=time.sleep, max_retries=0, max_delay=30.0
):
    """Stop at the first uncertainty; recovery is evidence, not permission to continue.

    An ambiguous create is never sent again, even if search finds nothing: search may
    lag behind writes. A single label match is reported for callers to verify identity.
    Default policy stops on every write error, including 429. Callers may explicitly
    opt into bounded non-create 429 retries with max_retries > 0. Each attempt
    gets its own log number and rechecks updated before every edit.
    """
    frozen = Plan([Operation(**json.loads(json.dumps(asdict(op)))) for op in plan.operations])
    if frozen.plan_hash != plan.plan_hash:
        raise ValueError("plan changed after confirmation")
    if max_retries < 0 or max_delay < 0:
        raise ValueError("retry bounds must not be negative")
    outcome = Outcome("ok")
    serial = 0
    methods = {
        "create": port.create_issue,
        "edit": port.edit_issue,
        "link": port.add_link,
        "attach": port.attach_file,
        "set_property": port.set_property,
    }
    for index, op in enumerate(frozen.operations):
        attempts = 0
        while True:
            sent = False
            try:
                if op.kind == "edit":
                    current = port.get_issue(op.payload["key"])
                    if current.get("fields", {}).get("updated") != op.expect_updated:
                        raise Conflict("updated changed; refresh the dry-run")
                serial += 1
                writelog.intent(
                    writelog_path,
                    run_id,
                    serial,
                    "sw-publish",
                    op.kind,
                    op.payload.get("key", scope_id),
                    f"plan={frozen.short_hash}",
                    f"index={index}",
                    op.idempotency_note,
                )
                sent = True
                result = methods[op.kind](**op.payload)
                writelog.result(writelog_path, run_id, serial, "ok")
                outcome.results.append(result)
                outcome.completed += 1
                break
            except (JiraError, OSError, ValueError, KeyError, TypeError) as exc:
                if sent:
                    # A timeout result records uncertainty rather than claiming the write failed.
                    detail = (
                        "ambiguous"
                        if isinstance(exc, Timeout) and exc.ambiguous
                        else type(exc).__name__
                    )
                    writelog.result(writelog_path, run_id, serial, "error", detail)
                if isinstance(exc, RateLimited) and op.kind != "create" and attempts < max_retries:
                    delay = max(exc.retry_after, 2**attempts)
                    if delay <= max_delay:
                        sleep(delay)
                        attempts += 1
                        continue
                outcome.status = "stopped"
                outcome.failed_index = index
                outcome.error = type(exc).__name__
                if op.kind == "create" and isinstance(exc, Timeout):
                    fields = op.payload.get("fields", {})
                    project = fields.get("project", {})
                    project = project.get("key") if isinstance(project, dict) else project
                    labels = [
                        label for label in fields.get("labels", []) if label.startswith("feat:")
                    ]
                    if project and len(labels) == 1:
                        try:
                            outcome.recovery_matches = port.search_by_label(project, labels[0])
                            outcome.recovered = len(outcome.recovery_matches) == 1
                            outcome.status = "recovered" if outcome.recovered else "not-recovered"
                        except JiraError:
                            outcome.status = "not-recovered"
                    else:
                        outcome.status = "not-recovered"
                return outcome
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.plan.read_text(encoding="utf-8"))
        plan = Plan([Operation(**op) for op in data["operations"]], data.get("plan_hash", ""))
        print(json.dumps({"plan_hash": plan.plan_hash, "short_hash": plan.short_hash}))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
