"""Offline-first licensing and entitlement system.

This package implements the Free / Premium / Pro / Super / Enterprise tier
model described in ``docs/development/FEATURE_GAP_ANALYSIS_AND_ROADMAP.md``.

Design principles:
* **Offline-first.** Activation and every subsequent validation work with no
  network at all; a license is a signed file bound to a machine fingerprint.
* **Privacy.** Only a SHA-256 digest of hardware identifiers is ever stored;
  raw identifiers never leave the machine.
* **Fail safe, fail closed to *usable*.** Any error reading or verifying the
  license degrades to the Free tier instead of crashing startup - a broken
  license must never take the cleaner down with it.

Public API::

    from cortex_unified.licensing import gating
    gating.allowed(Feature.SENTINEL_PRO)      # -> bool
    gating.require(Feature.GAMING_MODE)       # raises EntitlementError if gated
    from cortex_unified.licensing.license_manager import get_license_manager
    mgr = get_license_manager()
    mgr.status()                              # -> LicenseState
"""

from __future__ import annotations

from .gating import EntitlementError, allowed, current_tier, effective_features, require
from .license_manager import LicenseState, LicenseManager, get_license_manager
from .tiers import Feature, Tier

__all__ = [
    "EntitlementError",
    "Feature",
    "LicenseManager",
    "LicenseState",
    "Tier",
    "allowed",
    "current_tier",
    "effective_features",
    "get_license_manager",
    "require",
]
