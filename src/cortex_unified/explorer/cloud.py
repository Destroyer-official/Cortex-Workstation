"""Cloud integration module.

Bridge re-exporting the orphaned native backend
(``NexusExplorer.native.nexus_cloud``: CloudManager + OneDrive/Google/
Dropbox/S3 providers) for GUI use, e.g.::

    from cortex_unified.explorer.cloud import CloudManager, CloudProviderType
"""
from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


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
