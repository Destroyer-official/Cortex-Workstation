"""Cortex Cleaner Explorer Subsystem.

High-performance native Qt6 file manager module integrated into Cortex Cleaner.
Provides dual-pane browsing, FastCDC & Rust FFI transfers, archive extraction,
cloud integration, instant search indexer, and undo/redo operation history.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

# Ensure native directory is discoverable regardless of install location
_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


try:
    from NexusExplorer.native.nexus_core import (  # type: ignore
        FileTableModel,
        SortProxy as SortFilterProxy,
        fmt_ms,
        human,
    )
except ImportError:
    try:
        from nexus_core import (  # type: ignore
            FileTableModel,
            SortProxy as SortFilterProxy,
            fmt_ms,
            human,
        )
    except ImportError:
        FileTableModel = SortFilterProxy = fmt_ms = human = None  # type: ignore

try:
    from cortex_unified.engine.models import FileEntry  # type: ignore
except ImportError:
    FileEntry = None  # type: ignore

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
