"""Tests for the offline licensing / entitlement system.

Covers: fingerprint stability, tier math, license lifecycle (activate,
tamper, corrupt, wrong machine, expiry + grace, trial-once, deactivate) and
the gating API. Everything runs against a temp-path LicenseManager so the
developer's real ``~/.cortex_cleaner/license.json`` is never touched.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from cortex_unified.licensing import (
    EntitlementError,
    Feature,
    Tier,
    allowed,
    current_tier,
    effective_features,
)
from cortex_unified.licensing.fingerprint import (
    compute_fingerprint,
    get_fingerprint,
)
from cortex_unified.licensing.gating import gate
from cortex_unified.licensing.license_manager import (
    GRACE_DAYS,
    LicenseManager,
)
from cortex_unified.licensing.tiers import FEATURE_MIN_TIER, features_for_tier


@pytest.fixture()
def manager(tmp_path: Path) -> LicenseManager:
    """LicenseManager isolated to a temp file (real license untouched)."""
    return LicenseManager(path=tmp_path / "license.json")


# -- fingerprint ---------------------------------------------------------------


class TestFingerprint:
    """TestFingerprint."""
    def test_stable_across_calls(self):
        """test_stable_across_calls."""
        assert compute_fingerprint() == compute_fingerprint()

    def test_memoised_matches_direct(self):
        """test_memoised_matches_direct."""
        assert get_fingerprint() == compute_fingerprint()

    def test_shape(self):
        """test_shape."""
        digest = get_fingerprint()
        assert len(digest) == 64
        int(digest, 16)  # hex parseable

    def test_identifiers_never_empty(self):
        """test_identifiers_never_empty."""
        from cortex_unified.licensing import fingerprint as fp

        assert fp.collect_identifiers()


# -- tiers ---------------------------------------------------------------------


class TestTiers:
    """TestTiers."""
    def test_rank_ordering(self):
        """test_rank_ordering."""
        order = [Tier.FREE, Tier.PREMIUM, Tier.PRO, Tier.SUPER, Tier.ENTERPRISE]
        ranks = [t.rank for t in order]
        assert ranks == sorted(ranks)

    def test_includes_is_cumulative(self):
        """test_includes_is_cumulative."""
        assert Tier.ENTERPRISE.includes(Tier.FREE)
        assert Tier.PRO.includes(Tier.PREMIUM)
        assert not Tier.FREE.includes(Tier.PRO)

    def test_parse_defaults_to_free_on_garbage(self):
        """test_parse_defaults_to_free_on_garbage."""
        assert Tier.parse("pro") is Tier.PRO
        assert Tier.parse("GOLD") is Tier.FREE
        assert Tier.parse(None) is Tier.FREE

    def test_feature_matrix_cumulative(self):
        """test_feature_matrix_cumulative."""
        free = features_for_tier(Tier.FREE)
        pro = features_for_tier(Tier.PRO)
        premium = features_for_tier(Tier.PREMIUM)
        assert Feature.ENGINE_CLEAN in free
        assert Feature.GAMING_MODE in premium and Feature.GAMING_MODE not in free
        assert premium < pro
        # Every feature must have a matrix entry (no accidental denials).
        assert set(Feature) == set(FEATURE_MIN_TIER)


# -- license lifecycle ------------------------------------------------------------


class TestLicenseLifecycle:
    """TestLicenseLifecycle."""
    def test_fresh_machine_is_free(self, manager: LicenseManager):
        """test_fresh_machine_is_free."""
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert not state.licensed
        assert not state.trial

    def test_activate_and_validate(self, manager: LicenseManager):
        """test_activate_and_validate."""
        state = manager.activate("TEST-KEY-1", Tier.PRO, name="Tester")
        assert state.tier is Tier.PRO
        assert state.licensed
        assert state.key == "TEST-KEY-1"
        assert Feature.SENTINEL_PRO in state.features

    def test_key_masked_in_status(self, manager: LicenseManager):
        """test_key_masked_in_status."""
        manager.activate("VERYSECRET-1234", Tier.PRO)
        raw = json.dumps(manager.status())
        assert "VERYSECRET" not in raw

    def test_signature_tamper_rejected(self, manager: LicenseManager):
        """test_signature_tamper_rejected."""
        manager.activate("K", Tier.SUPER)
        doc = json.loads(manager._path.read_text(encoding="utf-8"))
        doc["payload"]["tier"] = "enterprise"
        manager._path.write_text(json.dumps(doc), encoding="utf-8")
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert "signature" in state.reason

    def test_payload_tamper_rejected(self, manager: LicenseManager):
        """test_payload_tamper_rejected."""
        manager.activate("K", Tier.PRO)
        doc = json.loads(manager._path.read_text(encoding="utf-8"))
        doc["signature"] = "0" * 64
        manager._path.write_text(json.dumps(doc), encoding="utf-8")
        assert manager.validate().tier is Tier.FREE

    def test_corrupt_file_degrades_to_free(self, manager: LicenseManager):
        """test_corrupt_file_degrades_to_free."""
        manager.activate("K", Tier.PRO)
        manager._path.write_text("{not json!!", encoding="utf-8")
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert "corrupt" in state.reason

    def test_wrong_machine_rejected(self, manager: LicenseManager):
        """test_wrong_machine_rejected."""
        manager.activate("K", Tier.PRO)
        doc = json.loads(manager._path.read_text(encoding="utf-8"))
        doc["payload"]["fingerprint"] = "f" * 64  # another machine's digest
        doc["signature"] = __import__(
            "cortex_unified.licensing.license_manager",
            fromlist=["LicensePayload"],
        ).LicensePayload.from_dict(doc["payload"]).sign()
        manager._path.write_text(json.dumps(doc), encoding="utf-8")
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert "machine" in state.reason

    def test_expiry_freezes_after_grace(self, tmp_path: Path):
        """test_expiry_freezes_after_grace."""
        manager = LicenseManager(path=tmp_path / "license.json")
        state = manager.activate("K", Tier.PRO, term_days=1)
        assert state.licensed
        # Backdate issued/expiry beyond the grace window, re-sign honestly.
        from cortex_unified.licensing.license_manager import LicensePayload

        payload = LicensePayload(
            key=state.key, tier=Tier.PRO, name="", email="",
            issued=(date.today() - timedelta(days=GRACE_DAYS + 5)).isoformat(),
            expiry=(date.today() - timedelta(days=GRACE_DAYS + 2)).isoformat(),
            fingerprint=get_fingerprint(),
        )
        document = {
            "version": 1,
            "payload": json.loads(payload.canonical()),
            "signature": payload.sign(),
        }
        manager._path.write_text(json.dumps(document), encoding="utf-8")
        manager._cache = None
        expired = manager.validate()
        assert expired.tier is Tier.FREE
        assert not expired.licensed
        assert "grace period ended" in expired.reason

    def test_grace_period_keeps_access(self, tmp_path: Path):
        """test_grace_period_keeps_access."""
        manager = LicenseManager(path=tmp_path / "license.json")
        from cortex_unified.licensing.license_manager import LicensePayload

        payload = LicensePayload(
            key="K", tier=Tier.PRO,
            issued=date.today().isoformat(),
            expiry=(date.today() - timedelta(days=1)).isoformat(),  # yesterday
            fingerprint=get_fingerprint(),
        )
        document = {
            "version": 1,
            "payload": json.loads(payload.canonical()),
            "signature": payload.sign(),
        }
        manager._path.write_text(json.dumps(document), encoding="utf-8")
        state = manager.validate()
        assert state.grace_active
        assert state.licensed  # grace keeps working access
        assert Feature.SENTINEL_PRO in state.features

    def test_trial_once_only(self, manager: LicenseManager):
        """test_trial_once_only."""
        state = manager.start_trial()
        assert state.trial and state.tier is Tier.PRO
        with pytest.raises(RuntimeError):
            manager.start_trial()

    def test_trial_refused_when_licensed(self, manager: LicenseManager):
        """test_trial_refused_when_licensed."""
        manager.activate("OWNED", Tier.SUPER)
        with pytest.raises(RuntimeError):
            manager.start_trial()

    def test_deactivate_returns_to_free(self, manager: LicenseManager):
        """test_deactivate_returns_to_free."""
        manager.activate("K", Tier.PRO)
        manager.deactivate()
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert not manager._path.exists()

    def test_activate_rejects_bad_input(self, manager: LicenseManager):
        """test_activate_rejects_bad_input."""
        with pytest.raises(ValueError):
            manager.activate("", Tier.PRO)
        with pytest.raises(ValueError):
            manager.activate("K", Tier.PRO, term_days=-3)

    def test_singleton_resettable(self):
        """test_singleton_resettable."""
        from cortex_unified.licensing.license_manager import (
            get_license_manager,
            reset_singleton,
        )

        first = get_license_manager()
        reset_singleton()
        second = get_license_manager()
        assert first is not second


# -- gating --------------------------------------------------------------------


class TestGating:
    """TestGating."""
    @pytest.fixture(autouse=True)
    def _licensed_pro(self, monkeypatch, tmp_path):
        """Point the singleton at a temp PRO license for every test here."""
        from cortex_unified.licensing import license_manager as lm_module

        manager = LicenseManager(path=tmp_path / "license.json")
        manager.activate("GATE-KEY", Tier.PRO)
        monkeypatch.setattr(lm_module, "_MANAGER", manager, raising=False)
        yield
        lm_module.reset_singleton()

    def test_current_tier_and_features(self):
        """test_current_tier_and_features."""
        assert current_tier() is Tier.PRO
        feats = effective_features()
        assert Feature.SENTINEL_PRO in feats
        assert Feature.POLICY_FILES not in feats  # enterprise-only

    def test_allowed_and_require(self):
        """test_allowed_and_require."""
        assert allowed(Feature.SENTINEL_PRO)
        require = __import__(
            "cortex_unified.licensing.gating", fromlist=["require"]
        ).require
        require(Feature.SENTINEL_PRO)  # no raise
        with pytest.raises(EntitlementError):
            require(Feature.POLICY_FILES)

    def test_entitlement_error_details(self):
        """test_entitlement_error_details."""
        require = __import__(
            "cortex_unified.licensing.gating", fromlist=["require"]
        ).require
        with pytest.raises(EntitlementError) as excinfo:
            require(Feature.AUDIT_EXPORT)
        assert excinfo.value.required is Tier.ENTERPRISE
        assert excinfo.value.current is Tier.PRO

    def test_gate_decorator_blocks_and_passes(self):
        """test_gate_decorator_blocks_and_passes."""
        @gate(Feature.SENTINEL_PRO)
        def pro_tool():
            """pro_tool."""
            return "ran"

        @gate(Feature.POLICY_FILES)
        def enterprise_tool():
            """enterprise_tool."""
            return "ran"

        assert pro_tool() == "ran"
        with pytest.raises(EntitlementError):
            enterprise_tool()
