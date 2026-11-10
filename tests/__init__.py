"""Make the shared library importable when tests run from the repository root."""

import sys
from pathlib import Path

LIB = Path(__file__).resolve().parent.parent / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
