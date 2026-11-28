#!/usr/bin/env python3
"""Optional Jira status sync. Files and git are the record; Jira only mirrors status.

    status_sync.py enable  [--off]                 opt in (or out): sets jira.status_sync
    status_sync.py plan    [--feat FEAT-NNN ...] [--remote KEY=Status ...]
    status_sync.py confirm --confirm "SYNC <SCOPE> <hash>" [same --feat/--remote]

The plan derives each published feature's local state from its files (spec, review, accepted,
planned, shipped, withdrawn), maps it to a Jira status (manifest `jira.status_map`, else the
default below) and compares it with the remote status the agent read with jira-read and passed
as --remote. Rows: `transition` (remote behind), `none`, `drift` (Jira ahead of the files:
reported, never pulled back), `read` (remote status not supplied). Execution is a session
jira-write transition per row, only after a fresh yes to this exact plan (its token).

Exit codes: 0 plan printed or confirmed, 1 confirm mismatch, 2 blocked or usage.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(f"error: shared library missing at {_shared}/kitlib; reinstall this skill")
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import frontmatter, fsio, miniyaml, workspace  # noqa: E402

DEFAULT_MAP = {
    "accepted": "To Do",
    "planned": "Ready for Dev",
    "shipped": "Done",
    "withdrawn": "Won't Do",
}
ACCEPTED = ("ready-to-publish", "published", "ready-for-dev", "in-development")


def _registry(base: Path) -> dict[str, str]:
    """Spec ID (unqualified) → Jira key, from .metadata/id-registry.md."""
    path = base / ".metadata" / "id-registry.md"
    out, header = {}, None
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set("".join(cells)) <= {"-"}:
            continue
        row = dict(zip(header, cells, strict=False))
        key = row.get("Jira key", "")
        if key and key not in ("—", "-", ""):
            out[row.get("Spec ID", "").split(":")[-1]] = key
    return out


def local_state(base: Path, feat: str) -> str:
    story = base / "02-drafts" / f"{feat}.story.md"
    if not story.is_file():
        return "unknown"
    fm = frontmatter.parse(story.read_text(encoding="utf-8")).fm or {}
    status = fm.get("status")
    if status == "withdrawn":
        return "withdrawn"
    if fm.get("shipped") or fm.get("merged_into"):
        return "shipped"
    if fm.get("origin") == "as-is" and status in ACCEPTED:
        return "shipped"  # version 1 of a live feature
    if status in ACCEPTED:
        tasks = base / "03-plan" / f"{feat}.tasks.md"
        if tasks.is_file():
            tfm = frontmatter.parse(tasks.read_text(encoding="utf-8")).fm or {}
            if tfm.get("status") == "ready":
                return "planned"
        return "accepted"
    if status == "in-review":
        return "review"
    if status == "superseded":
        return "withdrawn"
    return "spec"


def plan(base: Path, scope: str, manifest: dict, feats: list[str], remote: dict[str, str]) -> dict:
    jira = manifest.get("jira") if isinstance(manifest.get("jira"), dict) else {}
    blocked = []
    if str(jira.get("site") or "TBD") == "TBD":
        blocked.append("Jira is not configured (workspace.py jira set)")
    if jira.get("status_sync") is not True:
        blocked.append("status sync is off (status_sync.py enable, after the owner's yes)")
    mapping = {**DEFAULT_MAP, **(jira.get("status_map") or {})}
    keys = _registry(base)
    rows = []
    for feat in sorted(feats or keys):
        key = keys.get(feat)
        if not key:
            continue
        state = local_state(base, feat)
        want = mapping.get(state)
        have = remote.get(key)
        if want is None:
            action = "none"
        elif have is None:
            action = "read"
        elif have == want:
            action = "none"
        elif state != "shipped" and have == mapping.get("shipped"):
            action = "drift"
        else:
            action = "transition"
        rows.append(
            {
                "feature": feat,
                "key": key,
                "local": state,
                "target": want,
                "remote": have,
                "action": action,
            }
        )
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:12]
    unread = [r["key"] for r in rows if r["action"] == "read"]
    if unread:
        blocked.append("read the remote status first: " + ", ".join(unread))
    return {
        "scope": scope,
        "rows": rows,
        "transitions": [r for r in rows if r["action"] == "transition"],
        "drift": [r for r in rows if r["action"] == "drift"],
        "blocked": blocked,
        "token": None if blocked else f"SYNC {scope} {digest}",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("command", choices=["enable", "plan", "confirm"])
    parser.add_argument("--feat", action="append", default=[])
    parser.add_argument(
        "--remote", action="append", default=[], help="KEY=Status read via jira-read"
    )
    parser.add_argument("--confirm")
    parser.add_argument("--off", action="store_true")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--scope")
    args = parser.parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise ValueError("no workspace")
        scope = workspace.resolve(root, args.scope, args.feat[0] if args.feat else None, cwd, True)
        base = workspace.scope_dir(root, scope)
        mpath = base / workspace.FLAT_MANIFEST
        manifest = workspace.load(mpath)
        if args.command == "enable":
            jira = manifest.get("jira") if isinstance(manifest.get("jira"), dict) else {}
            jira["status_sync"] = not args.off
            manifest["jira"] = jira
            fsio.atomic_write(mpath, miniyaml.dumps(manifest))
            print(json.dumps({"status_sync": jira["status_sync"]}))
            return 0
        remote = {}
        for pair in args.remote:
            key, _, status = pair.partition("=")
            if not status:
                raise ValueError(f"--remote needs KEY=Status, got {pair!r}")
            remote[key.strip()] = status.strip()
        result = plan(base, scope, manifest, [f.split(":")[-1] for f in args.feat], remote)
        if args.command == "plan":
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 2 if result["blocked"] else 0
        ok = bool(result["token"]) and args.confirm == result["token"]
        print(json.dumps({"confirmed": ok, "transitions": result["transitions"] if ok else []}))
        return 0 if ok else 1
    except workspace.AskUser as exc:
        print(f"{exc} options: {exc.options}", file=sys.stderr)
        return 2
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
