"""Tier and feature definitions for Cortex Cleaner.

A *tier* is the licensed edition of the product (Free, Premium, Pro, Super,
Enterprise). A *feature* is one gated capability. The single source of truth
for "which tier unlocks which feature" is :data:`FEATURE_MIN_TIER` below - GUI
pages, CLI commands and engine modules all query it through
:mod:`cortex_unified.licensing.gating`, never by hard-coding tier names.

The mapping is cumulative: a tier unlocks every feature whose minimum tier is
at or below it, so adding a new tier later cannot accidentally re-lock
features from lower tiers.
"""

from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    """Licensed editions, ordered cheapest to most capable."""

    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"
    SUPER = "super"
    ENTERPRISE = "enterprise"

    @property
    def rank(self) -> int:
        """Monotonic capability rank; higher unlocks strictly more."""
        return _TIER_ORDER[self]

    def includes(self, minimum: "Tier") -> bool:
        """True if this tier satisfies a feature's minimum-tier requirement."""
        return self.rank >= minimum.rank

    @classmethod
    def parse(cls, value: str | None) -> "Tier":
        """Parse user/server supplied text into a Tier (Free on garbage)."""
        try:
            return cls((value or "").strip().lower())
        except ValueError:
            return cls.FREE


_TIER_ORDER: dict[Tier, int] = {
    Tier.FREE: 0,
    Tier.PREMIUM: 1,
    Tier.PRO: 2,
    Tier.SUPER: 3,
    Tier.ENTERPRISE: 4,
}


class Feature(str, Enum):
    """Stable identifiers of every gateable capability.

    Names never change once shipped because licenses reference them; new
    capabilities are appended, existing ones are only ever widened (their
    minimum tier lowered).
    """

    # -- Free core (explicitly listed so the matrix stays auditable) --------
    ENGINE_CLEAN = "engine.clean"
    DUPLICATES = "duplicates"
    LARGE_FILES = "large_files"
    PRIVACY_CLEAN = "privacy.clean"
    SCHEDULER = "scheduler"
    REPORTS = "reports"

    # -- Premium -------------------------------------------------------------
    SHRED_MULTIPASS = "shred.multipass"          # DoD 5220.22-M multi-pass
    FREE_SPACE_WIPE = "shred.free_space_wipe"    # cipher /w style wipe
    GAMING_MODE = "boost.gaming_mode"
    MEMORY_OPTIMIZER = "boost.memory_optimizer"
    VISUALIZATION_EXPORT = "reports.visualization_export"

    # -- Pro -------------------------------------------------------------------
    SENTINEL_PRO = "security.sentinel_pro"       # secrets scanner
    NETWORK_SUITE = "network.suite"              # discovery/audit/load test
    REGISTRY_CLEANER = "system.registry_cleaner"
    TELEMETRY_BLOCKER = "privacy.telemetry_blocker"
    AUTO_CLEAN_RULES = "scheduler.auto_clean_rules"

    # -- Super -----------------------------------------------------------------
    COMPONENT_STORE_TOOLS = "advanced.component_store"
    VDISK_MANAGER = "advanced.vdisk_manager"
    VULNERABILITY_CATALOG = "security.vulnerability_catalog"
    WAN_AUDIT = "network.wan_audit"
    EXPERIMENTAL_FEATURES = "advanced.experimental"

    # -- Enterprise --------------------------------------------------------------
    POLICY_FILES = "enterprise.policy_files"
    AUDIT_EXPORT = "enterprise.audit_export"


#: Minimum tier required for each feature. Anything absent defaults to Free.
FEATURE_MIN_TIER: dict[Feature, Tier] = {
    # Free core
    Feature.ENGINE_CLEAN: Tier.FREE,
    Feature.DUPLICATES: Tier.FREE,
    Feature.LARGE_FILES: Tier.FREE,
    Feature.PRIVACY_CLEAN: Tier.FREE,
    Feature.SCHEDULER: Tier.FREE,
    Feature.REPORTS: Tier.FREE,
    # Premium
    Feature.SHRED_MULTIPASS: Tier.PREMIUM,
    Feature.FREE_SPACE_WIPE: Tier.PREMIUM,
    Feature.GAMING_MODE: Tier.PREMIUM,
    Feature.MEMORY_OPTIMIZER: Tier.PREMIUM,
    Feature.VISUALIZATION_EXPORT: Tier.PREMIUM,
    # Pro
    Feature.SENTINEL_PRO: Tier.PRO,
    Feature.NETWORK_SUITE: Tier.PRO,
    Feature.REGISTRY_CLEANER: Tier.PRO,
    Feature.TELEMETRY_BLOCKER: Tier.PRO,
    Feature.AUTO_CLEAN_RULES: Tier.PRO,
    # Super
    Feature.COMPONENT_STORE_TOOLS: Tier.SUPER,
    Feature.VDISK_MANAGER: Tier.SUPER,
    Feature.VULNERABILITY_CATALOG: Tier.SUPER,
    Feature.WAN_AUDIT: Tier.SUPER,
    Feature.EXPERIMENTAL_FEATURES: Tier.SUPER,
    # Enterprise
    Feature.POLICY_FILES: Tier.ENTERPRISE,
    Feature.AUDIT_EXPORT: Tier.ENTERPRISE,
}


def features_for_tier(tier: Tier) -> set[Feature]:
    """Every feature unlocked by *tier* (cumulative across tiers below it)."""
    return {f for f, minimum in FEATURE_MIN_TIER.items() if tier.includes(minimum)}
