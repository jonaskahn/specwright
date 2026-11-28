#!/usr/bin/env python3
"""Delegate workspace operations without duplicating manifest rules.

Exit codes: 0 success, 2 usage or invalid workspace, 3 scope choice required.
The delegated argparse interface supplies --help.
"""

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

from kitlib import workspace  # noqa: E402


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    return workspace.main(argv)


if __name__ == "__main__":
    sys.exit(main())
