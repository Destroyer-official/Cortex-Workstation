"""Cloud integration module.

Bridge re-exporting the orphaned native backend
(``NexusExplorer.native.nexus_cloud``: CloudManager + OneDrive/Google/
Dropbox/S3 providers) for GUI use, e.g.::

    from cortex_unified.explorer.cloud import CloudManager, CloudProviderType
"""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native import nexus_cloud as _mod
except ImportError:
    import nexus_cloud as _mod  # type: ignore

# Explicit bridge names consumed by the GUI (Cloud page). Bound here so
# ``from cortex_unified.explorer.cloud import CloudManager`` is reliable
# and greppable; the dynamic loop below keeps any additional backend
# names available without further edits.
CloudManager = _mod.CloudManager
CloudProvider = _mod.CloudProvider
CloudProviderType = _mod.CloudProviderType
CloudFile = _mod.CloudFile
CloudAccount = _mod.CloudAccount
SyncStatus = _mod.SyncStatus
OneDriveProvider = _mod.OneDriveProvider
GoogleDriveProvider = _mod.GoogleDriveProvider
DropboxProvider = _mod.DropboxProvider
S3Provider = _mod.S3Provider
retry_on_rate_limit = _mod.retry_on_rate_limit

__all__ = [
    "CloudManager",
    "CloudProvider",
    "CloudProviderType",
    "CloudFile",
    "CloudAccount",
    "SyncStatus",
    "OneDriveProvider",
    "GoogleDriveProvider",
    "DropboxProvider",
    "S3Provider",
    "retry_on_rate_limit",
]
for _name in __all__:
    globals()[_name] = getattr(_mod, _name)
