#!/usr/bin/env python3
"""Create and change questions, decisions, reservations, splits and registry rows.

Every command validates first. With --dry-run it prints the plan and writes nothing; otherwise it
logs the write, rebuilds the trace and graph, and undoes itself on failure. Registry cells are
checked against the owner given by --as.

`backup <path>` archives the exact bytes of one authored artifact under _meta/history/ just before
an accepted requirement edit.

Exit codes: 0 done, 2 invalid request or unreadable data, 3 a human must supply something first
(for example the approvers), 4 the skill does not own a registry column.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import dataformat, ingest_impact, recordops, rtm, schema, workspace  # noqa: E402

COMMON = {
    "--cwd": {"default": "."},
    "--scope": {"help": "project scope; needed in a program"},
    "--as": {"dest": "skill", "default": "sw-shape", "help": "skill that owns this write"},
    "--format": {"choices": ["text", "json"], "default": "text"},
}


def _add(sub, name, help_text):
    cmd = sub.add_parser(name, help=help_text)
    for flag, kwargs in COMMON.items():
        cmd.add_argument(flag, **kwargs)
    cmd.add_argument("--dry-run", action="store_true", help="show the plan; write nothing")
    return cmd


def _decider(cmd):
    cmd.add_argument("--decided-by-role", default="")
    cmd.add_argument("--decided-by-name", default="")
    cmd.add_argument("--decided-by-account", default="")
    cmd.add_argument(
        "--evidence-kind", default="", help="omit all decider flags to record the owner (self)"
    )
    cmd.add_argument("--evidence-ref", default="")


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    top = parser.add_subparsers(dest="noun", required=True)

    q = top.add_parser("q", help="questions").add_subparsers(dest="verb", required=True)
    new = _add(q, "new", "record a question")
    new.add_argument("--title", required=True)
    new.add_argument("--affects", action="append", default=[], help="item it blocks; repeatable")
    new.add_argument("--owner", required=True)
    new.add_argument("--due", default="")
    new.add_argument("--raised-from", action="append", default=[], help="SRC-0001:L12-L14")
    new.add_argument("--quote", default="", help="must appear inside the cited lines")
    new.add_argument("--why", default="")
    new.add_argument("--option", action="append", default=[])
    new.add_argument("--default", default="")
    new.add_argument(
        "--non-blocking",
        action="store_true",
        help="--status assumed needs this and a --default: the default was applied",
    )
    new.add_argument("--status", choices=["proposed", "open", "assumed"], default="proposed")
    answer = _add(q, "answer", "answer a question and record the decision")
    answer.add_argument("id")
    answer.add_argument("--answer", required=True)
    answer.add_argument(
        "--amend", action="append", default=[], help="'FEAT-001||current wording||proposed wording'"
    )
    _decider(answer)
    withdraw = _add(q, "withdraw", "withdraw a question; its ID stays")
    withdraw.add_argument("id")
    withdraw.add_argument("--reason", required=True)

    amd = top.add_parser("amend", help="pending wording amendments").add_subparsers(
        dest="verb", required=True
    )
    anew = _add(amd, "new", "track a wording change an answer implies")
    anew.add_argument("--feat", required=True)
    anew.add_argument("--quote", required=True, help="current wording, exactly as saved")
    anew.add_argument("--proposed", required=True)
    anew.add_argument("--decision", default="")
    anew.add_argument("--source", default="", help="SRC-0001:L12-L14")
    aapply = _add(amd, "apply", "mark applied once the draft carries the proposed wording")
    aapply.add_argument("id")
    areject = _add(amd, "reject", "reject an amendment")
    areject.add_argument("id")
    areject.add_argument("--reason", required=True)

    dec = top.add_parser("dec", help="decisions").add_subparsers(dest="verb", required=True)
    dnew = _add(dec, "new", "record a decision with its evidence")
    dnew.add_argument("--title", required=True)
    dnew.add_argument("--affects", action="append", default=[])
    dnew.add_argument("--decision", default="")
    dnew.add_argument("--context", default="")
    dnew.add_argument("--supersedes", action="append", default=[])
    _decider(dnew)

    res = top.add_parser("reserve", help="reserve IDs").add_subparsers(dest="verb", required=True)
    feat = _add(res, "feat", "reserve features")
    feat.add_argument("--item", action="append", default=[], help="'Title|alias1,alias2'")
    epic = _add(res, "epic", "create an epic")
    epic.add_argument("--title", required=True)
    epic.add_argument("--scopes", help="comma-separated projects taking part, home first")
    epic.add_argument(
        "--bo", action="append", default=[], help="business objective it serves; repeat for more"
    )

    split = _add(top, "accept-split", "reserve features, fill an epic, record the decision")
    split.add_argument("--item", action="append", default=[], help="'Title|alias1,alias2'")
    split.add_argument("--existing", action="append", default=[], help="an already reserved FEAT")
    split.add_argument("--from-register", metavar="GROUP", help="every legacy item of this group")
    split.add_argument("--epic", action="append", default=[])
    split.add_argument("--new-epic", default="")
    split.add_argument("--bo", action="append", default=[], help="objectives of the new epic")
    _decider(split)

    bak = _add(top, "backup", "archive an authored artifact just before an accepted edit")
    bak.add_argument("path", help="project-relative path, e.g. 02-drafts/FEAT-001.md")

    reg = _add(top, "register", "set registry cells (ownership checked)")
    reg.add_argument("key")
    reg.add_argument("--set", action="append", default=[], metavar="COLUMN=VALUE", dest="cells")
    return parser


def _who(ctx, args):
    return recordops.decision_fields(
        ctx,
        args.decided_by_role,
        args.decided_by_name,
        args.decided_by_account,
        args.evidence_kind,
        args.evidence_ref,
    )


def _build(ctx, args):
    """(plan, action, target) for the parsed command."""
    if args.noun == "q" and args.verb == "new":
        plan = recordops.question_new(
            ctx,
            args.title,
            args.affects,
            args.owner,
            args.due,
            args.raised_from,
            args.quote,
            args.why,
            args.option,
            args.default,
            not args.non_blocking,
            args.status,
        )
        return plan, "q-new", ctx.scope + ":" + plan.made[0]
    if args.noun == "q" and args.verb == "answer":
        plan = recordops.question_answer(ctx, args.id, args.answer, _who(ctx, args), args.amend)
        return plan, "q-answer", f"{ctx.scope}:{args.id}"
    if args.noun == "q":
        plan = recordops.question_withdraw(ctx, args.id, args.reason)
        return plan, "q-withdraw", f"{ctx.scope}:{args.id}"
    if args.noun == "amend" and args.verb == "new":
        plan, identity = recordops.amendment_new(
            ctx, args.feat, args.quote, args.proposed, args.decision, args.source
        )
        return plan, "amend-new", f"{ctx.scope}:{identity}"
    if args.noun == "amend":
        outcome = "applied" if args.verb == "apply" else "rejected"
        plan = recordops.amendment_close(ctx, args.id, outcome, getattr(args, "reason", ""))
        return plan, f"amend-{args.verb}", f"{ctx.scope}:{args.id}"
    if args.noun == "dec":
        plan, identity = recordops.decision_new(
            ctx,
            args.title,
            args.affects,
            _who(ctx, args),
            args.decision,
            args.context,
            args.supersedes,
        )
        return plan, "dec-new", f"{ctx.scope}:{identity}"
    if args.noun == "reserve" and args.verb == "feat":
        plan = recordops.reserve_features(ctx, args.item)
        return plan, "reserve-feat", ", ".join(plan.made)
    if args.noun == "reserve":
        scopes = [s.strip() for s in args.scopes.split(",")] if args.scopes else None
        plan, identity = recordops.reserve_epic(ctx, args.title, scopes, bo=args.bo)
        return plan, "reserve-epic", f"{ctx.scope}:{identity}"
    if args.noun == "accept-split":
        items, existing = list(args.item), list(args.existing)
        if args.from_register:
            more_items, more_existing = recordops.register_group(ctx, args.from_register)
            items += more_items
            existing += more_existing
        plan = recordops.accept_split(
            ctx, items, existing, args.epic, args.new_epic, _who(ctx, args), args.bo
        )
        return plan, "accept-split", ", ".join(plan.made)
    cells = {}
    for pair in args.cells:
        name, _, value = pair.partition("=")
        cells[name.strip()] = value.strip()
    if not cells:
        raise recordops.RecordError("register needs --set COLUMN=VALUE")
    unknown = set(cells) - set(schema.REGISTRY_COLUMNS[1:])
    if unknown:
        raise recordops.RecordError(f"unknown registry columns: {sorted(unknown)}")
    denied = set(cells) - rtm.REGISTRY_OWNERS.get(args.skill, set())
    if denied:
        raise rtm.OwnershipError(f"{args.skill} does not own registry columns: {sorted(denied)}")
    return recordops.register(ctx, args.key, cells), "register", args.key


def _backup(root, scope, args):
    base = workspace.scope_dir(root, scope)
    if args.dry_run:
        print(f"plan:\n  back up {args.path} under _meta/history/")
        return 0
    target = ingest_impact.backup(base, args.path)
    print(f"done:\n  {target.relative_to(base)}")
    return 0


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        cwd = Path(args.cwd).resolve()
        root = workspace.find_root(cwd)
        if root is None:
            raise recordops.RecordError("no workspace; run the sw-start workspace setup first")
        scope = workspace.resolve(root, args.scope, None, cwd, True)
        if args.noun == "backup":
            return _backup(root, scope, args)
        ctx = recordops.Ctx(root, scope, args.skill)
        plan, action, target = _build(ctx, args)
        warnings = [] if args.dry_run else recordops.execute(ctx, plan, action, target)
        if not args.dry_run:
            for kind in ("records", "registry"):
                dataformat.refresh(root, kind, scope)
        result = {
            "dry_run": args.dry_run,
            "made": plan.made,
            "plan": plan.summary,
            "warnings": warnings,
        }
        if args.format == "json":
            print(json.dumps(result, indent=1))
        else:
            print(("plan:" if args.dry_run else "done:") + "\n  " + "\n  ".join(plan.summary))
            for line in warnings:
                print(f"warning: {line}", file=sys.stderr)
        return 0
    except rtm.OwnershipError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except (recordops.AskError, workspace.AskUser) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except (recordops.RecordError, ValueError, OSError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
