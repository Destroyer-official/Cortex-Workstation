"""Undo and redo file operation history stack."""
from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


try:
    from NexusExplorer.native.nexus_undo import (
        UndoStack,
        UndoEntry,
        OpKind,
    )
except ImportError:
    try:
        from nexus_undo import (  # type: ignore
            UndoStack,
            UndoEntry,
            OpKind,
        )
    except ImportError:
        UndoStack = UndoEntry = OpKind = None  # type: ignore

__all__ = [
    "UndoStack",
    "UndoEntry",
    "OpKind",
]
