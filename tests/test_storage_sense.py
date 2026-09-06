"""Tests for the Storage Sense config reader (interpretation + gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.storage_sense import StorageSense

IS_WINDOWS = platform.system() == "Windows"


class TestInterpret:
    """Group testinterpret tests covering unconfigured; enabled weekly; recycle bin config; downloads config; low space cadence; unknown cadence is custom."""
    def test_unconfigured(self):
        """Verify unconfigured via StorageSense._interpret."""
        s = StorageSense._interpret({})
        assert s["configured"] is False
        assert s["enabled"] is False

    def test_enabled_weekly(self):
        """Verify enabled weekly via StorageSense._interpret."""
        s = StorageSense._interpret({"01": 1, "2048": 7})
        assert s["enabled"] is True
        assert s["cadence"] == 7
        assert s["cadence_label"] == "Every week"

    def test_recycle_bin_config(self):
        """Verify recycle bin config via StorageSense._interpret."""
        s = StorageSense._interpret({"01": 1, "08": 1, "256": 30})
        assert s["recycle_bin_cleanup"] is True
        assert s["recycle_bin_days"] == 30
        assert s["recycle_bin_days_label"] == "30 days"

    def test_downloads_config(self):
        """Verify downloads config via StorageSense._interpret."""
        s = StorageSense._interpret({"32": 1, "512": 14})
        assert s["downloads_cleanup"] is True
        assert s["downloads_days_label"] == "14 days"

    def test_low_space_cadence(self):
        """Verify low space cadence via StorageSense._interpret."""
        s = StorageSense._interpret({"01": 1, "2048": 0})
        assert s["cadence_label"] == "When disk space is low"

    def test_unknown_cadence_is_custom(self):
        """Verify unknown cadence is custom via StorageSense._interpret."""
        s = StorageSense._interpret({"2048": 3})
        assert s["cadence_label"] == "Custom"


class TestValidation:
    """Group testvalidation tests covering set cadence rejects bad; set recycle days rejects bad."""
    def test_set_cadence_rejects_bad(self):
        """Verify set cadence rejects bad via StorageSense, msg.lower, set_cadence."""
        ok, msg = StorageSense().set_cadence(999)
        assert ok is False and "invalid" in msg.lower()

    def test_set_recycle_days_rejects_bad(self):
        """Verify set recycle days rejects bad via StorageSense, set_recycle_bin_days."""
        ok, msg = StorageSense().set_recycle_bin_days(999)
        assert ok is False


class TestSupport:
    """Group testsupport tests covering is supported; get status shape."""
    def test_is_supported(self):
        """Verify is supported via StorageSense.is_supported."""
        assert StorageSense.is_supported() == IS_WINDOWS

    def test_get_status_shape(self):
        """Verify get status shape via StorageSense, get_status."""
        s = StorageSense().get_status()
        assert "supported" in s
        if not IS_WINDOWS:
            assert s["supported"] is False
