#!/usr/bin/env python3
"""Check and copy durable citations of the form SRC-0001:L12-L14#a1b2.

verify checks that every cited line exists, is not blank and still matches its hash, and reports
sources that were superseded or are index-only pages. rebase lists where each citation of an old
source lands in a new one; it never rewrites a record. quote copies the exact cited text, and
stamp prints the citation with its hash, so nobody retypes either.

Exit codes: 0 clean, 1 findings, 2 usage or unreadable data, 3 the scope must be chosen.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import cite, workspace  # noqa: E402


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, help_text):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--cwd", default=".")
        cmd.add_argument("--scope", help="project scope; needed in a program")
        return cmd

    verify = add("verify", "check every citation in a file or folder")
    verify.add_argument("path", nargs="?", help="file or folder; default is the whole project")
    verify.add_argument("--require-hash", action="store_true", help="demand a #hash on each")
    verify.add_argument("--format", choices=["text", "json"], default="text")
    rebase = add("rebase", "show where citations of an old source land in a new one")
    rebase.add_argument("old")
    rebase.add_argument("new")
    quote = add("quote", "print the exact cited lines")
    quote.add_argument("citation")
    stamp = add("stamp", "print the citation with its hash filled in")
    stamp.add_argument("citation")
    return parser


def _context(args):
    cwd = Path(args.cwd).resolve()
    root = workspace.find_root(cwd)
    if root is None:
        raise ValueError("no workspace; run the sw-start workspace setup first")
    scope = workspace.resolve(root, args.scope, None, cwd, False)
    return workspace.scope_dir(root, scope), scope


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        base, _scope = _context(args)
        if args.command == "verify":
            target = Path(args.path).resolve() if args.path else base
            found = cite.verify(base, target, args.require_hash)
            if args.format == "json":
                rows = [
                    {
                        "file": f,
                        "line": p.line,
                        "code": p.code,
                        "severity": p.severity,
                        "msg": p.message,
                    }
                    for f, p in found
                ]
                print(json.dumps({"findings": rows}, indent=1))
            else:
                for rel, p in found:
                    print(f"{rel}:{p.line}: {p.severity} {p.code} {p.message}")
                if not found:
                    print("citations clean")
            return 1 if any(p.severity == "error" for _, p in found) else 0
        sources = cite.Sources(base)
        if args.command == "quote":
            print(cite.quote(sources, cite.parse_one(args.citation)))
            return 0
        if args.command == "stamp":
            print(cite.stamp(sources, cite.parse_one(args.citation)))
            return 0
        old_id, new_id = args.old.split(":")[-1], args.new.split(":")[-1]
        citing = []
        for path in cite.documents(base):
            rel = path.relative_to(base).as_posix()
            citing += [(rel, c) for c in cite.find(path.read_text(encoding="utf-8"))]
        rows = cite.rebase(sources, cite.Sources(base), old_id, new_id, citing)
        print("file\tline\told\tproposed\tnote")
        for row in rows:
            print("\t".join(str(x) for x in row))
        return 1 if any(not r[3] for r in rows) else 0
    except workspace.AskUser as ask:
        print(f"{ask} options: {ask.options}", file=sys.stderr)
        return 3
    except (OSError, ValueError, workspace.WorkspaceError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
