"""Fluent Qt6 File Explorer Widget module."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native.nexus_explorer import (
        DARK_QSS,
        CrumbBar,
        DebugOverlay,
        ExplorerWidget,
        PreviewPane,
        FileChecksumDialog,
        ShortcutsDialog,
        NexusClipboard,
        StagingShelfWidget,
        StagedItemRow,
    )
except ImportError:
    try:
        from nexus_explorer import (  # type: ignore
            DARK_QSS,
            CrumbBar,
            DebugOverlay,
            ExplorerWidget,
            PreviewPane,
            FileChecksumDialog,
            ShortcutsDialog,
            NexusClipboard,
            StagingShelfWidget,
            StagedItemRow,
        )
    except ImportError:
        DARK_QSS = CrumbBar = DebugOverlay = ExplorerWidget = PreviewPane = None  # type: ignore
        FileChecksumDialog = ShortcutsDialog = NexusClipboard = StagingShelfWidget = StagedItemRow = None  # type: ignore

__all__ = [
    "DARK_QSS",
    "CrumbBar",
    "DebugOverlay",
    "ExplorerWidget",
    "PreviewPane",
    "FileChecksumDialog",
    "ShortcutsDialog",
    "NexusClipboard",
    "StagingShelfWidget",
    "StagedItemRow",
]
