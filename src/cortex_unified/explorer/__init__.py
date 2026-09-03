"""Cortex Cleaner Explorer Subsystem.

High-performance native Qt6 file manager module integrated into Cortex Cleaner.
Provides dual-pane browsing, FastCDC & Rust FFI transfers, archive extraction,
cloud integration, instant search indexer, and undo/redo operation history.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure native directory is discoverable if needed
_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native.nexus_core import (  # type: ignore
        FileEntry,
        FileTableModel,
        SortFilterProxy,
        fmt_ms,
        human,
    )
except ImportError:
    try:
        from nexus_core import (  # type: ignore
            FileEntry,
            FileTableModel,
            SortFilterProxy,
            fmt_ms,
            human,
        )
    except ImportError:
        FileEntry = FileTableModel = SortFilterProxy = fmt_ms = human = None  # type: ignore

try:
    from NexusExplorer.native.nexus_explorer import (  # type: ignore
        DARK_QSS,
        CrumbBar,
        DebugOverlay,
        ExplorerWidget,
        PreviewPane,
    )
except ImportError:
    try:
        from nexus_explorer import (  # type: ignore
            DARK_QSS,
            CrumbBar,
            DebugOverlay,
            ExplorerWidget,
            PreviewPane,
        )
    except ImportError:
        ExplorerWidget = DARK_QSS = CrumbBar = DebugOverlay = PreviewPane = None  # type: ignore

__all__ = [
    "ExplorerWidget",
    "DARK_QSS",
    "CrumbBar",
    "PreviewPane",
    "DebugOverlay",
    "FileEntry",
    "FileTableModel",
    "SortFilterProxy",
    "human",
    "fmt_ms",
]
