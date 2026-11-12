#!/usr/bin/env python3
"""Check Python and Node 24, and install Node into the user's own folder after consent.

`check` and `plan` only read. `install node` refuses unless it is given --yes, which the agent
passes only after the user approves the exact plan in this session. Exit codes: 0 ok, 1 a
runtime is missing or too old, 2 usage or download failure, 3 consent missing.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import argparse
import json

from kitlib import runtime  # noqa: E402

EXIT_MISSING, EXIT_ERROR, EXIT_CONSENT = 1, 2, 3


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    chk = sub.add_parser("check", help="report Python, Node and npm")
    chk.add_argument("--format", choices=["text", "json"], default="text")
    sub.add_parser("plan", help="print what installing Node would do; change nothing").add_argument(
        "tool", choices=["node"]
    )
    inst = sub.add_parser("install", help="install Node for this user")
    inst.add_argument("tool", choices=["node"])
    inst.add_argument("--yes", action="store_true", help="the user approved the plan")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        if args.command == "check":
            status = runtime.check()
            if args.format == "json":
                print(json.dumps(status, indent=1))
            else:
                for name, item in status.items():
                    mark = "ok" if item["ok"] else "missing or too old"
                    print(f"{name}: {item['version'] or '-'} ({mark}; need {item['need']})")
            return 0 if all(item["ok"] for item in status.values()) else EXIT_MISSING
        if args.command == "plan":
            print("\n".join(runtime.plan_node()))
            return 0
        folder = runtime.install_node(yes=args.yes)
        print(f"installed: {folder}")
        return 0
    except runtime.RuntimeFault as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_CONSENT if "approval" in str(exc) else EXIT_ERROR
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
