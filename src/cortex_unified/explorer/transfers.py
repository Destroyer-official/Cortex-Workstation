"""File transfer queue and progress monitoring module."""

from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


try:
    from NexusExplorer.native.nexus_transfer_queue import TransferQueue, TransferJob
    from NexusExplorer.native.nexus_transfer_monitor import TransferMonitorDialog
except ImportError:
    try:
        from nexus_transfer_queue import TransferQueue, TransferJob  # type: ignore
        from nexus_transfer_monitor import TransferMonitorDialog  # type: ignore
    except ImportError:
        TransferQueue = TransferJob = TransferMonitorDialog = None  # type: ignore

# Backward compatibility alias
TransferMonitor = TransferMonitorDialog

__all__ = [
    "TransferQueue",
    "TransferJob",
    "TransferMonitorDialog",
    "TransferMonitor",
]
