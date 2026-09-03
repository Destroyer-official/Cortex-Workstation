"""The two config implementations must agree on safety-critical defaults.

Cortex carries a legacy flat config (:mod:`cortex_unified.core.config`, used by
44 modules) and a validated pydantic config
(:mod:`cortex_unified.core.config_v2`). Both previously declared their own
exclusion defaults, and they had silently drifted: ``config_v2`` protected
``.vscode``/``.idea`` while the legacy config every module actually uses did
not - so a real cleanup run could reach into editor state.

``config_v2.ScanConfig`` now derives its defaults from ``DEFAULT_CONFIG``.
These tests fail if anyone reintroduces a second source of truth.
"""

from __future__ import annotations

from cortex_unified.core.config import DEFAULT_CONFIG, Config
from cortex_unified.core.config_v2 import ScanConfig

#: Keys whose defaults decide what cleanup is allowed to touch.
_SAFETY_KEYS = (
    "exclude_patterns",
    "exclude_dirs",
    "exclude_regex_patterns",
    "min_age_days",
    "follow_symlinks",
)


def test_scan_defaults_match_the_legacy_baseline():
    """A drift here means two different answers to "what is protected?"."""
    scan = ScanConfig()
    for key in _SAFETY_KEYS:
        assert getattr(scan, key) == DEFAULT_CONFIG[key], (
            f"{key} diverged between config.DEFAULT_CONFIG and "
            f"config_v2.ScanConfig; derive it, don't restate it."
        )


def test_editor_state_directories_are_protected():
    """Regression: these were protected only by the unused config."""
    for name in (".git", "__pycache__", "node_modules", ".vscode", ".idea"):
        assert name in DEFAULT_CONFIG["exclude_dirs"], name
        assert name in ScanConfig().exclude_dirs, name
        # And the object real code constructs must protect them too.
        assert name in Config("does-not-exist.yaml").exclude_dirs, name


def test_v2_defaults_do_not_alias_the_shared_constant():
    """Deriving must copy: a mutation must not corrupt the shared baseline."""
    scan = ScanConfig()
    scan.exclude_dirs.append("mutated-by-test")
    scan.exclude_patterns.append("mutated-by-test")
    assert "mutated-by-test" not in DEFAULT_CONFIG["exclude_dirs"]
    assert "mutated-by-test" not in DEFAULT_CONFIG["exclude_patterns"]
    # A fresh instance must be unaffected too.
    assert "mutated-by-test" not in ScanConfig().exclude_dirs


def test_legacy_config_does_not_alias_the_shared_constant():
    """The CLI mutates ``config_data``; that must stay instance-local."""
    cfg = Config("does-not-exist.yaml")
    cfg.config_data["exclude_dirs"].append("mutated-by-test")
    assert "mutated-by-test" not in DEFAULT_CONFIG["exclude_dirs"]
    assert "mutated-by-test" not in Config("does-not-exist.yaml").exclude_dirs


def test_both_configs_expose_the_same_flat_accessors():
    """``config_v2`` must stay a drop-in for the legacy attribute surface."""
    legacy = Config("does-not-exist.yaml")
    scan = ScanConfig()
    for key in _SAFETY_KEYS:
        assert hasattr(legacy, key), key
        assert hasattr(scan, key), key
        assert getattr(legacy, key) == getattr(scan, key), key
