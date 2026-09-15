"""Native core file engine and table model."""
from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


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
