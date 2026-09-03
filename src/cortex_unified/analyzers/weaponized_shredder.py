"""Backward-compatibility alias for AdvancedShredder."""
from __future__ import annotations

import warnings
from cortex_unified.analyzers.advanced_shredder import AdvancedShredder, WeaponizedShredder

warnings.warn(
    "weaponized_shredder is deprecated; import AdvancedShredder from "
    "cortex_unified.analyzers.advanced_shredder instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["AdvancedShredder", "WeaponizedShredder"]
