#!/usr/bin/env python3
"""Read, check and export the data files other tools consume (_meta/data/).

The files follow one format (references/data-format.md). Each file has one owner skill, and
only that skill writes it: `export` refuses a kind the named skill does not own. `check` and
`show` only read. Exit codes: 0 ok, 1 invalid file, 2 usage or unreadable data, 4 stale or
missing file.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import dataformat, workspace  # noqa: E402

EXIT_INVALID, EXIT_ERROR, EXIT_STALE = 1, 2, 4


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope", help="one project; omit at a program root for all")
        return cmd

    export = add("export", "write one kind (or all the kinds the skill owns)")
    export.add_argument("kind", help="a data kind, or 'all' for every kind --as may write")
    export.add_argument("--as", dest="writer", required=True, help="the skill that owns the kind")
    chk = add("check", "report missing, invalid and stale files, and who refreshes each")
    chk.add_argument("--format", choices=["text", "json"], default="text")
    show = add("show", "print one data file")
    show.add_argument("kind")
    add("reindex", "rewrite only index.json from the files present")
    return parser


def _root(args):
    cwd = Path(args.cwd).resolve()
    root = workspace.find_root(cwd)
    if root is None:
        raise ValueError("no workspace; run the sw-start workspace setup first")
    scope = None
    if args.scope or workspace.mode_of(root) == "flat":
        scope = workspace.resolve(root, args.scope, None, cwd, True)
    return root, scope


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        root, scope = _root(args)
        if args.command == "export":
            kinds = (
                [k for k, v in sorted(dataformat.KINDS.items()) if args.writer in v.writers]
                if args.kind == "all"
                else [args.kind]
            )
            if not kinds:
                raise dataformat.DataError(f"{args.writer} owns no data kind")
            for kind in kinds:
                for path in dataformat.write_kind(root, kind, args.writer, scope):
                    print(f"wrote {path.relative_to(root)}")
            return 0
        if args.command == "reindex":
            for folder, _, scopes in dataformat.targets(root, scope):
                dataformat.reindex(root, folder, scopes)
                print(f"reindexed {folder.relative_to(root)}")
            return 0
        if args.command == "show":
            folder = dataformat.targets(root, scope)[-1][0]
            doc = dataformat.read(folder, args.kind)
            if doc is None:
                raise dataformat.DataError(f"{args.kind}.json is missing in {folder}")
            print(json.dumps(doc, indent=1, ensure_ascii=False))
            return 0
        findings = dataformat.check(root, scope)
        if args.format == "json":
            print(json.dumps({"findings": findings}, indent=1))
        else:
            for item in findings:
                print(item["message"])
                if item["command"]:
                    print(f"  run: {item['command']}")
            print("data clean" if not findings else f"{len(findings)} finding(s)")
        if any(f["status"] == "invalid" for f in findings):
            return EXIT_INVALID
        return EXIT_STALE if any(f["status"] in ("stale", "missing") for f in findings) else 0
    except (OSError, ValueError, workspace.WorkspaceError, dataformat.DataError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
