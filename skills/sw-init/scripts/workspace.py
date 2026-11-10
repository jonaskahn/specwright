#!/usr/bin/env python3
"""Delegate workspace operations without duplicating manifest rules.

Exit codes: 0 success, 2 usage or invalid workspace, 3 scope choice required.
The delegated argparse interface supplies --help.
"""

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
for _base in (_here, *_here.parents):
    if (_base / "kitlib").is_dir() or (_base / "lib" / "kitlib").is_dir():
        sys.path.insert(0, str(_base if (_base / "kitlib").is_dir() else _base / "lib"))
        break

from kitlib import fsio, workspace  # noqa: E402


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    result = workspace.main(argv)
    if result == 0 and argv and argv[0] == "init":
        # Shared initialization owns manifests; this wrapper adds portable standing rules.
        args = workspace._build_parser().parse_args(argv)
        root = Path(args.root).resolve()
        source = _here.parent / "assets/standing-rules.md"
        try:
            text = source.read_text(encoding="utf-8")
            for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
                target = root / name
                if not target.exists():
                    fsio.atomic_write(target, text)
                    print(f"  {name}")
        except OSError as exc:
            print(f"error: standing rules could not be installed: {exc}", file=sys.stderr)
            return 2
    return result


if __name__ == "__main__":
    sys.exit(main())
