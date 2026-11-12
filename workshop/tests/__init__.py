"""Make the canonical shared library importable when tests run from the repository root."""

import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parents[2] / "skills" / "_shared" / "scripts"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))
