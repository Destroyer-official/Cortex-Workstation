"""Fast background filesystem indexing engine."""
from __future__ import annotations

import sys
from pathlib import Path

_NATIVE_DIR = Path(__file__).resolve().parents[2] / "NexusExplorer" / "native"
if _NATIVE_DIR.is_dir() and str(_NATIVE_DIR) not in sys.path:
    sys.path.insert(0, str(_NATIVE_DIR))

try:
    from NexusExplorer.native import nexus_indexer as _mod
except ImportError:
    import nexus_indexer as _mod  # type: ignore

__all__ = getattr(_mod, "__all__", [k for k in dir(_mod) if not k.startswith("_")])
for _name in __all__:
    globals()[_name] = getattr(_mod, _name)
