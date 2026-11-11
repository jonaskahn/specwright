"""Load tools/draw_shells.py once so drawing tests render against the merged full tree.

The shipped skill carries only the core and extended diagram types; the rest live under
``extras/sw-spec``. ``draw_shells`` lays the two over each other in a temporary directory so
the whole closed roster stays rendered, checked and tested.
"""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if "draw_shells" in sys.modules:
    SHELLS = sys.modules["draw_shells"]
else:
    _spec = importlib.util.spec_from_file_location("draw_shells", ROOT / "tools/draw_shells.py")
    SHELLS = importlib.util.module_from_spec(_spec)
    sys.modules["draw_shells"] = SHELLS
    _spec.loader.exec_module(SHELLS)

SCRIPTS = SHELLS.SCRIPTS
