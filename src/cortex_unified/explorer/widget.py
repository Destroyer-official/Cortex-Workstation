"""Fluent Qt6 File Explorer Widget module."""

from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


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
