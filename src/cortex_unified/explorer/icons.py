"""Vector icon pipeline for Explorer subsystem."""
from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


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
