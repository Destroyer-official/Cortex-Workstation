"""Tests for the Storage Sense config reader (interpretation + gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.storage_sense import StorageSense

IS_WINDOWS = platform.system() == "Windows"


class TestInterpret:
    """TestInterpret."""
    def test_unconfigured(self):
        """test_unconfigured."""
        s = StorageSense._interpret({})
        assert s["configured"] is False
        assert s["enabled"] is False

    def test_enabled_weekly(self):
        """test_enabled_weekly."""
        s = StorageSense._interpret({"01": 1, "2048": 7})
        assert s["enabled"] is True
        assert s["cadence"] == 7
        assert s["cadence_label"] == "Every week"

    def test_recycle_bin_config(self):
        """test_recycle_bin_config."""
        s = StorageSense._interpret({"01": 1, "08": 1, "256": 30})
        assert s["recycle_bin_cleanup"] is True
        assert s["recycle_bin_days"] == 30
        assert s["recycle_bin_days_label"] == "30 days"

    def test_downloads_config(self):
        """test_downloads_config."""
        s = StorageSense._interpret({"32": 1, "512": 14})
        assert s["downloads_cleanup"] is True
        assert s["downloads_days_label"] == "14 days"

    def test_low_space_cadence(self):
        """test_low_space_cadence."""
        s = StorageSense._interpret({"01": 1, "2048": 0})
        assert s["cadence_label"] == "When disk space is low"

    def test_unknown_cadence_is_custom(self):
        """test_unknown_cadence_is_custom."""
        s = StorageSense._interpret({"2048": 3})
        assert s["cadence_label"] == "Custom"


class TestValidation:
    """TestValidation."""
    def test_set_cadence_rejects_bad(self):
        """test_set_cadence_rejects_bad."""
        ok, msg = StorageSense().set_cadence(999)
        assert ok is False and "invalid" in msg.lower()

    def test_set_recycle_days_rejects_bad(self):
        """test_set_recycle_days_rejects_bad."""
        ok, msg = StorageSense().set_recycle_bin_days(999)
        assert ok is False


class TestSupport:
    """TestSupport."""
    def test_is_supported(self):
        """test_is_supported."""
        assert StorageSense.is_supported() == IS_WINDOWS

    def test_get_status_shape(self):
        """test_get_status_shape."""
        s = StorageSense().get_status()
        assert "supported" in s
        if not IS_WINDOWS:
            assert s["supported"] is False
