#!/usr/bin/env python3
"""Pin the newest Node 24 release: write its archive names and sha256 values into the kit.

Run by a maintainer when Node 24 gets a new patch. The pins ship in the skills as
``runtime-pins.tsv``, read by runtime.sh and runtime.ps1, so nothing is trusted on first use:
the installer checks every download against these values.
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "skills/_shared/scripts/runtime-pins.tsv"
SOURCE = "https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt"
PLATFORMS = {
    "darwin-arm64": "tar.gz",
    "darwin-x64": "tar.gz",
    "linux-arm64": "tar.gz",
    "linux-x64": "tar.gz",
    "win-x64": "zip",
}
HEADER = "# Pinned Node release: platform, archive, sha256. Written by pin_node.py.\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail when the pins are not current")
    args = parser.parse_args(argv)
    with urllib.request.urlopen(SOURCE, timeout=30) as response:  # noqa: S310 (fixed https URL)
        text = response.read().decode("utf-8")
    pins = {}
    version = ""
    for line in text.splitlines():
        digest, _, name = line.partition("  ")
        found = re.fullmatch(r"node-v(24\.\d+\.\d+)-(.+)\.(tar\.gz|zip)", name.strip())
        if found and PLATFORMS.get(found.group(2)) == found.group(3):
            version = found.group(1)
            pins[found.group(2)] = (name.strip(), digest)
    if set(pins) != set(PLATFORMS):
        print(f"error: missing platforms: {sorted(set(PLATFORMS) - set(pins))}", file=sys.stderr)
        return 2
    rows = "".join(f"{key}\t{name}\t{digest}\n" for key, (name, digest) in sorted(pins.items()))
    content = f"{HEADER}base\thttps://nodejs.org/dist/v{version}\n{rows}"
    if args.check:
        return 0 if TARGET.read_text(encoding="utf-8") == content else 1
    TARGET.write_text(content, encoding="utf-8")
    print(f"pinned Node {version} in {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
