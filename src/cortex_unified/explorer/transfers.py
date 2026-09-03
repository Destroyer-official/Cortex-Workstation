"""File transfer queue and progress monitoring module."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

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
