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
    """Provide manager fixture via pytest.fixture, LicenseManager.

    Args:
        tmp_path (Path): Filesystem path to the target file or directory.

    Returns:
        LicenseManager: Result of the operation.
    """
    return LicenseManager(path=tmp_path / "license.json")


# -- fingerprint ---------------------------------------------------------------


class TestFingerprint:
    """Group testfingerprint tests covering stable across calls; memoised matches direct; shape; identifiers never empty."""
    def test_stable_across_calls(self):
        """Verify stable across calls via compute_fingerprint."""
        assert compute_fingerprint() == compute_fingerprint()

    def test_memoised_matches_direct(self):
        """Verify memoised matches direct via get_fingerprint, compute_fingerprint."""
        assert get_fingerprint() == compute_fingerprint()

    def test_shape(self):
        """Verify shape via get_fingerprint."""
        digest = get_fingerprint()
        assert len(digest) == 64
        int(digest, 16)  # hex parseable

    def test_identifiers_never_empty(self):
        """Verify identifiers never empty via fp.collect_identifiers."""
        from cortex_unified.licensing import fingerprint as fp

        assert fp.collect_identifiers()


# -- tiers ---------------------------------------------------------------------


class TestTiers:
    """Group testtiers tests covering rank ordering; includes is cumulative; parse defaults to free on garbage; feature matrix cumulative."""
    def test_rank_ordering(self):
        """Verify rank ordering via sorted."""
        order = [Tier.FREE, Tier.PREMIUM, Tier.PRO, Tier.SUPER, Tier.ENTERPRISE]
        ranks = [t.rank for t in order]
        assert ranks == sorted(ranks)

    def test_includes_is_cumulative(self):
        """Verify includes is cumulative via Tier.ENTERPRISE.includes, Tier.PRO.includes, Tier.FREE.includes."""
        assert Tier.ENTERPRISE.includes(Tier.FREE)
        assert Tier.PRO.includes(Tier.PREMIUM)
        assert not Tier.FREE.includes(Tier.PRO)

    def test_parse_defaults_to_free_on_garbage(self):
        """Verify parse defaults to free on garbage via Tier.parse."""
        assert Tier.parse("pro") is Tier.PRO
        assert Tier.parse("GOLD") is Tier.FREE
        assert Tier.parse(None) is Tier.FREE

    def test_feature_matrix_cumulative(self):
        """Verify feature matrix cumulative via features_for_tier."""
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
    """Group testlicenselifecycle tests covering fresh machine is free; activate and validate; key masked in status; signature tamper rejected; payload tamper rejected; corrupt file degrades to free."""
    def test_fresh_machine_is_free(self, manager: LicenseManager):
        """Verify fresh machine is free via manager.validate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert not state.licensed
        assert not state.trial

    def test_activate_and_validate(self, manager: LicenseManager):
        """Verify activate and validate via manager.activate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        state = manager.activate("TEST-KEY-1", Tier.PRO, name="Tester")
        assert state.tier is Tier.PRO
        assert state.licensed
        assert state.key == "TEST-KEY-1"
        assert Feature.SENTINEL_PRO in state.features

    def test_key_masked_in_status(self, manager: LicenseManager):
        """Verify key masked in status via manager.activate, json.dumps, manager.status.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("VERYSECRET-1234", Tier.PRO)
        raw = json.dumps(manager.status())
        assert "VERYSECRET" not in raw

    def test_signature_tamper_rejected(self, manager: LicenseManager):
        """Verify signature tamper rejected via manager.activate, json.loads, manager.validate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("K", Tier.SUPER)
        doc = json.loads(manager._path.read_text(encoding="utf-8"))
        doc["payload"]["tier"] = "enterprise"
        manager._path.write_text(json.dumps(doc), encoding="utf-8")
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert "signature" in state.reason

    def test_payload_tamper_rejected(self, manager: LicenseManager):
        """Verify payload tamper rejected via manager.activate, json.loads, json.dumps.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("K", Tier.PRO)
        doc = json.loads(manager._path.read_text(encoding="utf-8"))
        doc["signature"] = "0" * 64
        manager._path.write_text(json.dumps(doc), encoding="utf-8")
        assert manager.validate().tier is Tier.FREE

    def test_corrupt_file_degrades_to_free(self, manager: LicenseManager):
        """Verify corrupt file degrades to free via manager.activate, manager.validate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("K", Tier.PRO)
        manager._path.write_text("{not json!!", encoding="utf-8")
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert "corrupt" in state.reason

    def test_wrong_machine_rejected(self, manager: LicenseManager):
        """Verify wrong machine rejected via LicensePayload.from_dict, manager.activate, json.loads.

        Args:
            manager (LicenseManager): The manager parameter.
        """
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
        """Verify expiry freezes after grace via LicenseManager, manager.activate, LicensePayload.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.
        """
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
        """Verify grace period keeps access via LicenseManager, LicensePayload, manager.validate.

        Args:
            tmp_path (Path): Filesystem path to the target file or directory.
        """
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
        """Verify trial once only via manager.start_trial, pytest.raises.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        state = manager.start_trial()
        assert state.trial and state.tier is Tier.PRO
        with pytest.raises(RuntimeError):
            manager.start_trial()

    def test_trial_refused_when_licensed(self, manager: LicenseManager):
        """Verify trial refused when licensed via manager.activate, pytest.raises, manager.start_trial.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("OWNED", Tier.SUPER)
        with pytest.raises(RuntimeError):
            manager.start_trial()

    def test_deactivate_returns_to_free(self, manager: LicenseManager):
        """Verify deactivate returns to free via manager.activate, manager.deactivate, manager.validate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        manager.activate("K", Tier.PRO)
        manager.deactivate()
        state = manager.validate()
        assert state.tier is Tier.FREE
        assert not manager._path.exists()

    def test_activate_rejects_bad_input(self, manager: LicenseManager):
        """Verify activate rejects bad input via pytest.raises, manager.activate.

        Args:
            manager (LicenseManager): The manager parameter.
        """
        with pytest.raises(ValueError):
            manager.activate("", Tier.PRO)
        with pytest.raises(ValueError):
            manager.activate("K", Tier.PRO, term_days=-3)

    def test_singleton_resettable(self):
        """Verify singleton resettable via get_license_manager, reset_singleton."""
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
    """Group testgating tests covering current tier and features; allowed and require; entitlement error details; gate decorator blocks and passes."""
    @pytest.fixture(autouse=True)
    def _licensed_pro(self, monkeypatch, tmp_path):
        """Point the singleton at a temp PRO license for every test here.

        Args:
            monkeypatch: The monkeypatch parameter.
            tmp_path: Filesystem path to the target file or directory.
        """
        from cortex_unified.licensing import license_manager as lm_module

        manager = LicenseManager(path=tmp_path / "license.json")
        manager.activate("GATE-KEY", Tier.PRO)
        monkeypatch.setattr(lm_module, "_MANAGER", manager, raising=False)
        yield
        lm_module.reset_singleton()

    def test_current_tier_and_features(self):
        """Verify current tier and features via effective_features, current_tier."""
        assert current_tier() is Tier.PRO
        feats = effective_features()
        assert Feature.SENTINEL_PRO in feats
        assert Feature.POLICY_FILES not in feats  # enterprise-only

    def test_allowed_and_require(self):
        """Verify allowed and require via pytest.raises, allowed, require."""
        assert allowed(Feature.SENTINEL_PRO)
        require = __import__(
            "cortex_unified.licensing.gating", fromlist=["require"]
        ).require
        require(Feature.SENTINEL_PRO)  # no raise
        with pytest.raises(EntitlementError):
            require(Feature.POLICY_FILES)

    def test_entitlement_error_details(self):
        """Verify entitlement error details via pytest.raises, __import__, require."""
        require = __import__(
            "cortex_unified.licensing.gating", fromlist=["require"]
        ).require
        with pytest.raises(EntitlementError) as excinfo:
            require(Feature.AUDIT_EXPORT)
        assert excinfo.value.required is Tier.ENTERPRISE
        assert excinfo.value.current is Tier.PRO

    def test_gate_decorator_blocks_and_passes(self):
        """Verify gate decorator blocks and passes via pytest.raises, gate, pro_tool."""
        @gate(Feature.SENTINEL_PRO)
        def pro_tool():
            """Pro tool using gate."""
            return "ran"

        @gate(Feature.POLICY_FILES)
        def enterprise_tool():
            """Enterprise tool using gate."""
            return "ran"

        assert pro_tool() == "ran"
        with pytest.raises(EntitlementError):
            enterprise_tool()
