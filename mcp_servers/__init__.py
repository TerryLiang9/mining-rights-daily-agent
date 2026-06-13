"""MCP server packages."""

from __future__ import annotations

import sys
from pathlib import Path

_SHARED_PATH = Path(__file__).resolve().parents[1] / "packages" / "shared"
if _SHARED_PATH.exists():
    shared_path = str(_SHARED_PATH)
    if shared_path not in sys.path:
        sys.path.insert(0, shared_path)
