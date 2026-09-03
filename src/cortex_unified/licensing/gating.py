"""Entitlement checks: the single gateway every gated feature goes through.

GUI pages, CLI commands and engine modules must never inspect the license
directly. They call :func:`allowed` / :func:`require` here, so enforcement
policy (grace handling, upgrade nudges, audit logging) stays in one place.

Typical use in a tool module::

    from cortex_unified.licensing.gating import require

    class SentinelScanner:
        def run_scan(self, root):
            require(Feature.SENTINEL_PRO)
            ...

Typical use in a CLI command::

    @main.command()
    def secrets():
        \"\"\"Scan for exposed secrets (Pro).\"\"\"
        require(Feature.SENTINEL_PRO)
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TypeVar

from .license_manager import get_license_manager
from .tiers import Feature, Tier, features_for_tier

_LOG = logging.getLogger("cortex.licensing.gating")

T = TypeVar("T")


class EntitlementError(PermissionError):
    """Raised by :func:`require` when a feature's tier is not licensed."""

    def __init__(self, feature: Feature, required: Tier, current: Tier,
                 message: str | None = None):
        """__init__."""
        self.feature = feature
        self.required = required
        self.current = current
        super().__init__(
            message
            or f"'{feature.value}' requires the {required.value.title()} tier "
               f"(current tier: {current.value})."
        )
        """__init__."""
        """__init__."""


def current_tier() -> Tier:
    """The effective tier of this machine right now."""
    return get_license_manager().validate().tier


def effective_features() -> set[Feature]:
    """Every feature unlocked on this machine right now."""
    return features_for_tier(current_tier())


def allowed(feature: Feature) -> bool:
    """True if *feature* may be used right now (never raises)."""
    try:
        state = get_license_manager().validate()
    except Exception as exc:  # noqa: BLE001 - gating must never break callers
        _LOG.debug("license validation failed; denying %s: %s", feature.value, exc)
        return False
    if not state.allows(feature):
        _LOG.debug("feature denied: %s (tier=%s)", feature.value, state.tier.value)
        return False
    return True


def require(feature: Feature) -> None:
    """Raise :class:`EntitlementError` unless *feature* is licensed."""
    from .tiers import FEATURE_MIN_TIER

    required = FEATURE_MIN_TIER.get(feature, Tier.FREE)
    state = get_license_manager().validate()
    if not state.allows(feature):
        raise EntitlementError(feature, required, state.tier)


def gate(feature: Feature) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator form of :func:`require` for whole functions/methods."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """decorator."""
        def wrapper(*args: object, **kwargs: object) -> T:
            """wrapper."""
            require(feature)
            return func(*args, **kwargs)
            """wrapper."""
            """wrapper."""

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper
        """decorator."""
        """decorator."""

    return decorator


# -- test/diagnostics hooks ---------------------------------------------------

_RESET_LOCK = threading.Lock()


def reset_cache() -> None:
    """Drop memoised validation state (tests only)."""
    with _RESET_LOCK:
        get_license_manager().invalidate()
