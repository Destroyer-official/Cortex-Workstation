"""Tests for the free-space wiper (validation + platform gating).

We never run a real ``cipher /w`` here (it takes many minutes and rewrites the
whole volume). We test input validation, platform gating, and honest medium
reporting via a monkeypatched storage probe.
"""

from __future__ import annotations

import platform

from cortex_unified.system_tools.free_space_wipe import FreeSpaceWiper, WipeResult

IS_WINDOWS = platform.system() == "Windows"


class TestGating:
    """Group testgating tests covering is supported matches platform; non windows refuses."""
    def test_is_supported_matches_platform(self):
        """Verify is supported matches platform via FreeSpaceWiper.is_supported."""
        assert FreeSpaceWiper.is_supported() == IS_WINDOWS

    def test_non_windows_refuses(self):
        """Verify non windows refuses via pytest.skip, FreeSpaceWiper, wipe."""
        if IS_WINDOWS:
            import pytest
            pytest.skip("covered by validation tests on Windows")
        r = FreeSpaceWiper().wipe("C")
        assert isinstance(r, WipeResult)
        assert r.success is False


class TestValidation:
    """Group testvalidation tests covering rejects bad letter; rejects empty."""
    def test_rejects_bad_letter(self):
        """Verify rejects bad letter via pytest.skip, r.message.lower, FreeSpaceWiper."""
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only validation path")
        r = FreeSpaceWiper().wipe("not-a-letter")
        assert r.success is False
        assert "invalid" in r.message.lower()

    def test_rejects_empty(self):
        """Verify rejects empty via pytest.skip, FreeSpaceWiper, wipe."""
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only validation path")
        assert FreeSpaceWiper().wipe("").success is False


class TestMediumHonesty:
    """Group testmediumhonesty tests covering medium for reports effectiveness."""
    def test_medium_for_reports_effectiveness(self, monkeypatch):
        """Verify medium for reports effectiveness via monkeypatch.setattr, StorageInfo, FreeSpaceWiper.

        Args:
            monkeypatch: The monkeypatch parameter.
        """
        from cortex_unified.engine.models import StorageKind
        from cortex_unified.engine.storage import StorageInfo
        from cortex_unified.system_tools import free_space_wipe as mod

        monkeypatch.setattr(mod, "detect_storage",
                            lambda p: StorageInfo(StorageKind.SSD))
        medium, effective = FreeSpaceWiper().medium_for("C")
        assert medium == StorageKind.SSD.value
        assert effective == StorageKind.SSD.overwrite_effective
