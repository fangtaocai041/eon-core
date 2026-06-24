"""
unified_emergence.py — SHIM: canonical source at infrastructure/unified_emergence.py

All imports transparently forwarded via importlib.
"""

import sys
import importlib.util
from pathlib import Path

# Locate canonical emergence engine at infrastructure/unified_emergence.py
_CANONICAL = (
    Path(__file__).resolve().parent.parent.parent
    / "infrastructure" / "unified_emergence.py"
)
_spec = importlib.util.spec_from_file_location("unified_emergence", str(_CANONICAL))
_mod = importlib.util.module_from_spec(_spec)
sys.modules["unified_emergence"] = _mod
_spec.loader.exec_module(_mod)

# Copy all public names into this shim's namespace
for _name in dir(_mod):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_mod, _name)
