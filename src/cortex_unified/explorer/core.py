"""Native core file engine and table model."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native.nexus_core import (
        Engine,
        FileTableModel,
        IconThumbs,
        SortProxy,
        find_cli,
        fmt_ms,
        human,
    )
except ImportError:
    try:
        from nexus_core import (  # type: ignore
            Engine,
            FileTableModel,
            IconThumbs,
            SortProxy,
            find_cli,
            fmt_ms,
            human,
        )
    except ImportError:
        Engine = FileTableModel = IconThumbs = SortProxy = None  # type: ignore
        find_cli = fmt_ms = human = None  # type: ignore

__all__ = [
    "Engine",
    "FileTableModel",
    "IconThumbs",
    "SortProxy",
    "find_cli",
    "fmt_ms",
    "human",
]
