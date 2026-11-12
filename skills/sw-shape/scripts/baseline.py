#!/usr/bin/env python3
"""Start from an existing baseline: a legacy register of capabilities the business already runs.

import-register  normalize a legacy register into 01-analysis/baseline/register.tsv
propose-grouping group it and list the legacy items that have no feature yet
reserve          reserve one feature per legacy item of a group, keeping the legacy ID as an alias
brief            draft one idea brief per group and record the first question: keep each legacy
                 item as one feature, or re-split by INVEST

A reservation here maps a legacy item one to one and is provisional; it is not an accepted split.
The product owner decides the split, and `record.py accept-split` records that decision. Every write
supports --dry-run and is logged.

Exit codes: 0 done, 2 invalid request or unreadable data, 3 the scope must be chosen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _local_shared if _local_shared.is_dir() else _source_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib import baseline, fsio, index, recordops, workspace, writelog  # noqa: E402


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("import-register", "propose-grouping", "reserve", "brief"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope")
        cmd.add_argument("--dry-run", action="store_true")
        if name == "import-register":
            cmd.add_argument("file", type=Path)
            cmd.add_argument(
                "--source-id", help="a registered source; its legacy_id_pattern applies"
            )
            cmd.add_argument("--replace", action="store_true", help="overwrite a derived register")
        if name in ("reserve", "brief"):
            cmd.add_argument("--group")
            if name == "reserve":
                cmd.add_argument(
                    "--item",
                    help="reserve one legacy item by its ID instead of a whole group",
                )
        if name == "brief":
            cmd.add_argument("--owner", default="PO", help="who answers the first question")
    return parser


def _register(base: Path) -> list[dict[str, str]]:
    rows = index.read_register(base / baseline.REGISTER)
    if rows is None:
        raise baseline.BaselineError("no register yet; run import-register first")
    return rows


def _features_by_legacy(ctx: recordops.Ctx) -> dict[str, str]:
    """legacy ID (casefold) to the feature key that carries it as an alias."""
    mapping: dict[str, str] = {}
    for alias, key in recordops.alias_owners(ctx).items():
        if ":FEAT-" in key:
            mapping[alias] = key.split(":")[1]
    return mapping


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise baseline.BaselineError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, args.command != "propose-grouping")
        base = workspace.scope_dir(root, scope)
        ctx = recordops.Ctx(root, scope, "sw-shape")
        log = base / "_meta/write-log.md"
        if args.command == "import-register":
            pattern = ""
            if args.source_id:
                match = [
                    s for s in workspace.source_list(root, scope) if s.get("id") == args.source_id
                ]
                if not match:
                    raise baseline.BaselineError(f"source {args.source_id} is not registered")
                pattern = str(match[0].get("legacy_id_pattern", ""))
            rows = baseline.parse_register(args.file.read_text(encoding="utf-8"), pattern)
            target = base / baseline.REGISTER
            if target.exists() and not args.replace:
                raise baseline.BaselineError("a register exists; re-import with --replace")
            print(f"{len(rows)} legacy item(s) in {len(baseline.groups(rows))} group(s)")
            if args.dry_run:
                return 0
            with writelog.operation(log, "sw-shape", "baseline-register", scope) as op:
                fsio.atomic_write(target, baseline.render_register(rows))
                op.wrote(target)
            return 0
        rows = _register(base)
        grouped = baseline.groups(rows)
        mapped = set(_features_by_legacy(ctx))
        if args.command == "reserve" and args.item:
            found = next(
                (r for r in rows if r["legacy_id"].casefold() == args.item.casefold()), None
            )
            if found is None:
                raise baseline.BaselineError(
                    f"no legacy item '{args.item}'; IDs: {', '.join(r['legacy_id'] for r in rows)}"
                )
            todo = [found] if found["legacy_id"].casefold() not in mapped else []
            if not todo:
                print("this legacy item already has a feature")
                return 0
            plan = recordops.reserve_features(ctx, [baseline.item_arg(r) for r in todo])
            ids_text = ", ".join(f"{ctx.scope}:{i}" for i in plan.made)
            print(f"reserving {len(plan.made)} id(s): {ids_text}")
            print("plan:\n  " + "\n  ".join(plan.summary))
            if not args.dry_run:
                for line in recordops.execute(ctx, plan, "reserve-feat", ", ".join(plan.made)):
                    print(f"warning: {line}", file=sys.stderr)
            return 0
        if args.command == "propose-grouping":
            text = baseline.proposal_text(grouped, mapped)
            for group, items in grouped.items():
                open_items = [r for r in items if r["legacy_id"].casefold() not in mapped]
                print(f"{group}: {len(items)} item(s), {len(open_items)} without a feature")
            if not args.dry_run:
                target = base / baseline.PROPOSAL
                with writelog.operation(log, "sw-shape", "baseline-proposal", scope) as op:
                    fsio.atomic_write(target, text)
                    op.wrote(target)
            return 0
        if args.group not in grouped:
            raise baseline.BaselineError(f"no group '{args.group}'; groups: {', '.join(grouped)}")
        items = grouped[args.group]
        if args.command == "reserve":
            todo = [r for r in items if r["legacy_id"].casefold() not in mapped]
            if not todo:
                print("every legacy item of this group already has a feature")
                return 0
            plan = recordops.reserve_features(ctx, [baseline.item_arg(r) for r in todo])
            ids_text = ", ".join(f"{ctx.scope}:{i}" for i in plan.made)
            print(f"reserving {len(plan.made)} id(s): {ids_text}")
            print("plan:\n  " + "\n  ".join(plan.summary))
            if not args.dry_run:
                for line in recordops.execute(ctx, plan, "reserve-feat", ", ".join(plan.made)):
                    print(f"warning: {line}", file=sys.stderr)
            return 0
        features = _features_by_legacy(ctx)
        missing = [r["legacy_id"] for r in items if r["legacy_id"].casefold() not in features]
        if missing:
            raise baseline.BaselineError(
                "reserve this group first; no feature yet for " + ", ".join(missing)
            )
        sources = baseline.sources_for(base, items)
        identity, text = baseline.brief_text(scope, args.group, items, features, sources)
        target = base / "01-analysis/ideas" / (identity + ".md")
        if target.exists():
            raise baseline.BaselineError(f"{target.name} already exists")
        question = recordops.question_new(
            ctx,
            f"Keep each legacy item of {args.group} as one feature or re-split by INVEST",
            [features[r["legacy_id"].casefold()] for r in items],
            args.owner,
            why="The split decides the feature boundaries every later step builds on.",
            options=["Keep each legacy item as one feature", "Re-split by INVEST", "Defer"],
            default="keep the reserved features and the brief as drafts; no approval",
        )
        print(
            f"plan:\n  create {target.relative_to(base).as_posix()}\n  "
            + "\n  ".join(question.summary)
        )
        if args.dry_run:
            return 0
        question.creates[target] = text
        for line in recordops.execute(ctx, question, "baseline-brief", f"{scope}:{identity}"):
            print(f"warning: {line}", file=sys.stderr)
        return 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (
        baseline.BaselineError,
        recordops.RecordError,
        OSError,
        ValueError,
        workspace.WorkspaceError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
