"""Entitlement checks: the single gateway every gated feature goes through.

GUI pages, CLI commands and engine modules must never inspect the license
directly. They call :func:`allowed` / :func:`require` here.
Entitlement checks and debug logging of denials; grace handling and upgrade nudges are in license_manager.
This module only reads the resulting state.

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
    """Raised when a feature requires a higher tier.

    """

    def __init__(self, feature: Feature, required: Tier, current: Tier,
                 message: str | None = None):
        """Initialize the entitlement error with feature and tier context.

        Initializes the instance and configures internal state.

        Args:
            feature (Feature): The feature parameter.
            required (Tier): The required parameter.
            current (Tier): The current parameter.
            message (str | None): Informational or progress status message.
        """
        self.feature = feature
        self.required = required
        self.current = current
        super().__init__(
            message
            or f"'{feature.value}' requires the {required.value.title()} tier "
               f"(current tier: {current.value})."
        )


def current_tier() -> Tier:
    """The effective tier of this machine right now.


    Returns:
        Tier: Result of the operation.
    """
    return get_license_manager().validate().tier


def effective_features() -> set[Feature]:
    """Every feature unlocked on this machine right now.


    Returns:
        set[Feature]: Result of the operation.
    """
    return features_for_tier(current_tier())


def allowed(feature: Feature) -> bool:
    """Whether a feature is currently permitted, never raising.


    Args:
        feature (Feature): The feature parameter.

    Returns:
        bool: True if the operation succeeded, False otherwise.
    """
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
    """Raise EntitlementError unless the feature is permitted.


    Args:
        feature (Feature): The feature parameter.
    """
    from .tiers import FEATURE_MIN_TIER

    required = FEATURE_MIN_TIER.get(feature, Tier.FREE)
    state = get_license_manager().validate()
    if not state.allows(feature):
        raise EntitlementError(feature, required, state.tier)


def gate(feature: Feature) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorate a callable to require a feature before execution.


    Args:
        feature (Feature): The feature parameter.

    Returns:
        Callable[[Callable[..., T]], Callable[..., T]]: Result of the operation.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        """Wrap a function with an entitlement check preserving metadata.


        Args:
            func (Callable[..., T]): The func parameter.

        Returns:
            Callable[..., T]: Result of the operation.
        """
        def wrapper(*args: object, **kwargs: object) -> T:
            """Enforce the required feature then call the wrapped function.


            Returns:
                T: Result of the operation.
            """
            require(feature)
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper

    return decorator


# -- test/diagnostics hooks ---------------------------------------------------

_RESET_LOCK = threading.Lock()


def reset_cache() -> None:
    """Drop memoised validation state (tests only).

    """
    with _RESET_LOCK:
        get_license_manager().invalidate()
