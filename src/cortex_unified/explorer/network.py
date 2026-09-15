"""Network filesystem and remote share explorer."""
from __future__ import annotations

import sys
from pathlib import Path

from cortex_unified.core.utils import ensure_nexus_in_sys_path, get_nexus_native_dir

_NATIVE_DIR = get_nexus_native_dir() or (Path(__file__).resolve().parents[2] / "NexusExplorer" / "native")
ensure_nexus_in_sys_path()


try:
    from NexusExplorer.native.nexus_network import (  # type: ignore
        NetworkManager,
        NetworkProtocol,
        NetworkFS,
        NetworkFile,
        SMBProvider,
        FTPProvider,
        SFTPProvider,
        WebDAVProvider,
    )
    from NexusExplorer.native import nexus_network as _mod  # type: ignore
except ImportError:
    try:
        from nexus_network import (  # type: ignore
            NetworkManager,
            NetworkProtocol,
            NetworkFS,
            NetworkFile,
            SMBProvider,
            FTPProvider,
            SFTPProvider,
            WebDAVProvider,
        )
        import nexus_network as _mod  # type: ignore
    except ImportError:
        NetworkManager = NetworkProtocol = NetworkFS = NetworkFile = None  # type: ignore
        SMBProvider = FTPProvider = SFTPProvider = WebDAVProvider = None  # type: ignore
        _mod = None  # type: ignore

if _mod:
    __all__ = getattr(_mod, "__all__", [k for k in dir(_mod) if not k.startswith("_")])
    for _name in __all__:
        globals()[_name] = getattr(_mod, _name)

