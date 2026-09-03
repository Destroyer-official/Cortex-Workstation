"""Vector icon pipeline for Explorer subsystem."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native.nexus_icons import (
        icon,
        action_icon,
        sidebar_icon,
        folder_icon,
        icon_for_ext,
    )
except ImportError:
    try:
        from nexus_icons import (  # type: ignore
            icon,
            action_icon,
            sidebar_icon,
            folder_icon,
            icon_for_ext,
        )
    except ImportError:
        icon = action_icon = sidebar_icon = folder_icon = icon_for_ext = None  # type: ignore

__all__ = [
    "icon",
    "action_icon",
    "sidebar_icon",
    "folder_icon",
    "icon_for_ext",
]
