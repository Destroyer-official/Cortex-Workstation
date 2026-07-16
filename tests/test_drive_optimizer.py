"""Tests for the media-aware Drive Optimizer.

Critically verifies the safety rule: it must NEVER defragment an SSD/NVMe, even
when explicitly asked. Actual optimization is not run (it needs admin and takes
minutes); we test recommendation logic and the SSD-defrag refusal.
"""

from __future__ import annotations

import platform

from cortex_unified.engine.models import StorageKind
from cortex_unified.system_tools.drive_optimizer import (
    DriveOptimizer,
    OptimizeOp,
    OptimizeResult,
)

IS_WINDOWS = platform.system() == "Windows"


class TestRecommendation:
    def test_hdd_recommends_defrag(self):
        op, note = DriveOptimizer._recommend(StorageKind.HDD)
        assert op is OptimizeOp.DEFRAG

    def test_ssd_recommends_trim(self):
        op, note = DriveOptimizer._recommend(StorageKind.SSD)
        assert op is OptimizeOp.TRIM
        assert "never defragment" in note.lower()

    def test_nvme_recommends_trim(self):
        assert DriveOptimizer._recommend(StorageKind.NVME)[0] is OptimizeOp.TRIM

    def test_unknown_recommends_none(self):
        assert DriveOptimizer._recommend(StorageKind.UNKNOWN)[0] is OptimizeOp.NONE


class TestSafety:
    def test_is_supported_matches_platform(self):
        assert DriveOptimizer.is_supported() == IS_WINDOWS

    def test_list_drives_returns_list(self):
        assert isinstance(DriveOptimizer().list_drives(), list)

    def test_refuses_defrag_on_ssd(self, monkeypatch):
        """Even if the caller explicitly asks to DEFRAG an SSD, it must refuse."""
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only path")

        from cortex_unified.system_tools import drive_optimizer as mod
        from cortex_unified.engine.storage import StorageInfo

        # Force the probe to report SSD regardless of the real machine.
        monkeypatch.setattr(mod, "detect_storage",
                            lambda p: StorageInfo(StorageKind.SSD))
        result = DriveOptimizer().optimize("C", OptimizeOp.DEFRAG)
        assert isinstance(result, OptimizeResult)
        assert result.success is False
        assert result.op is OptimizeOp.NONE
        assert "harmful" in result.message.lower() or "refused" in result.message.lower()

    def test_non_windows_returns_unsupported(self):
        if IS_WINDOWS:
            import pytest
            pytest.skip("covered elsewhere on Windows")
        r = DriveOptimizer().optimize("C")
        assert r.success is False
