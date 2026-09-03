"""Undo and redo file operation history stack."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

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
