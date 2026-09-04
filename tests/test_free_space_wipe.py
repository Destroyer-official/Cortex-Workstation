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
    """Testgating.

    Manages TestGating operations and coordinates related state changes for the component.
    """
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform.

        Manages test is supported matches platform operations and coordinates related state changes for the component.
        """
        assert FreeSpaceWiper.is_supported() == IS_WINDOWS

    def test_non_windows_refuses(self):
        """test_non_windows_refuses.

        Manages test non windows refuses operations and coordinates related state changes for the component.
        """
        if IS_WINDOWS:
            import pytest
            pytest.skip("covered by validation tests on Windows")
        r = FreeSpaceWiper().wipe("C")
        assert isinstance(r, WipeResult)
        assert r.success is False


class TestValidation:
    """Testvalidation.

    Manages TestValidation operations and coordinates related state changes for the component.
    """
    def test_rejects_bad_letter(self):
        """test_rejects_bad_letter.

        Manages test rejects bad letter operations and coordinates related state changes for the component.
        """
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only validation path")
        r = FreeSpaceWiper().wipe("not-a-letter")
        assert r.success is False
        assert "invalid" in r.message.lower()

    def test_rejects_empty(self):
        """test_rejects_empty.

        Manages test rejects empty operations and coordinates related state changes for the component.
        """
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only validation path")
        assert FreeSpaceWiper().wipe("").success is False


class TestMediumHonesty:
    """Testmediumhonesty.

    Manages TestMediumHonesty operations and coordinates related state changes for the component.
    """
    def test_medium_for_reports_effectiveness(self, monkeypatch):
        """test_medium_for_reports_effectiveness.

        Manages test medium for reports effectiveness operations and coordinates related state changes for the component.

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
