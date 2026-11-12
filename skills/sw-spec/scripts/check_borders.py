#!/usr/bin/env python3
"""Check CSS edges with the shared L-024 rule; SVG lines are not CSS borders.

Exit codes: 0 clean, 1 findings, 2 usage or unreadable input.
"""

import argparse
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_source_shared = _here.parent.parent / "_shared" / "scripts"
_local_shared = _here.parent / "_shared" / "scripts"
_shared = _source_shared if _source_shared.is_dir() else _local_shared
if not (_shared / "kitlib").is_dir():
    sys.exit(
        f"error: shared library missing at {_shared}/kitlib; "
        "reinstall this skill from a zip that includes its _shared folder"
    )
if str(_shared) not in sys.path:
    sys.path.insert(0, str(_shared))

from kitlib.borders import find_one_sided  # noqa: E402

SUFFIXES = {".html", ".css", ".svg", ".md"}


def paths_for(paths):
    result = set()
    for raw in paths:
        path = Path(raw)
        if not path.exists():
            raise OSError(f"not found: {path}")
        if path.is_dir():
            result.update(p for p in path.rglob("*") if p.suffix in SUFFIXES and p.is_file())
        elif path.suffix in SUFFIXES:
            result.add(path)
        else:
            raise ValueError(f"unsupported file: {path}")
    return sorted(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args(argv)
    try:
        findings = [
            f"{path}:{line}: L-024 {message}"
            for path in paths_for(args.paths)
            for line, message in find_one_sided(path.read_text(encoding="utf-8"))
        ]
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for finding in findings:
        print(finding)
    return int(bool(findings))


if __name__ == "__main__":
    sys.exit(main())
