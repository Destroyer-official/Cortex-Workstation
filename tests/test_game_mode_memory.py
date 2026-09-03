"""Tests for Gaming Mode and the memory optimizer.

Windows-specific paths run only on Windows; the logic tests (protected-list
filtering, report serialization, dry-run semantics) run everywhere so CI on
Ubuntu stays green.
"""

from __future__ import annotations

import sys

import pytest

from cortex_unified.system_tools.game_mode import (
    _DEFAULT_SUSPEND_CANDIDATES,
    _PROTECTED,
    BoostReport,
    GameMode,
)
from cortex_unified.system_tools.memory_optimizer import (
    MemoryOptimizeResult,
    MemoryOptimizer,
    SystemRamMetrics,
)

IS_WINDOWS = sys.platform == "win32"


class TestGameModeLogic:
    """TestGameModeLogic."""
    def test_protected_never_in_candidates(self):
        """test_protected_never_in_candidates."""
        assert not (
            _PROTECTED & set(_DEFAULT_SUSPEND_CANDIDATES)
        ), "a suspend candidate must never also be protected"

    def test_boost_report_serializes(self):
        """test_boost_report_serializes."""
        report = BoostReport(ok=True, phase="start", power_to="High")
        report.suspended.append("OneDrive.exe")
        data = report.to_dict()
        assert data["ok"] is True
        assert data["phase"] == "start"
        assert "OneDrive.exe" in data["suspended"]

    def test_unsupported_reports_cleanly(self, monkeypatch):
        """test_unsupported_reports_cleanly."""
        game = GameMode()
        if not GameMode.is_supported():
            result = game.start()
            assert not result.ok
            assert "requires" in result.message
        else:  # supported here; force the unsupported branch instead
            monkeypatch.setattr(GameMode, "is_supported", staticmethod(lambda: False))
            result = game.start()
            assert not result.ok

    def test_stop_without_start_is_safe(self):
        """test_stop_without_start_is_safe."""
        game = GameMode(dry_run=True)
        report = game.stop()
        assert report.ok
        assert report.phase == "stop"


@pytest.mark.skipif(
    not IS_WINDOWS, reason="power plan + process suspension are Windows-only"
)
class TestGameModeWindows:
    """TestGameModeWindows."""
    def test_preview_is_read_only(self):
        """test_preview_is_read_only."""
        preview = GameMode().preview()
        assert preview["supported"] is True
        assert "would_suspend" in preview

    def test_dry_run_changes_nothing(self):
        """test_dry_run_changes_nothing."""
        game = GameMode(
            extra_suspend=("nonexistent_noise_process_xyz.exe",), dry_run=True
        )
        report = game.start()
        assert report.ok
        assert not game._suspended_pids  # nothing actually suspended
        assert not game._boosted_plan_guid  # no plan switch recorded
        game.stop()

    def test_pick_prefers_high_performance(self, tmp_path_factory):
        """test_pick_prefers_high_performance."""
        from cortex_unified.system_tools.performance_tuner import PowerPlan

        game = GameMode(dry_run=True)
        plans = [
            PowerPlan(guid="1" * 36, name="Balanced"),
            PowerPlan(guid="2" * 36, name="High performance"),
            PowerPlan(guid="3" * 36, name="Power saver"),
        ]
        picked = game._pick_boost_plan(plans)
        assert picked is not None
        assert picked.name == "High performance"

    def test_candidates_exclude_protected_and_self(self):
        """test_candidates_exclude_protected_and_self."""
        game = GameMode(
            extra_suspend=("explorer.exe", "svchost.exe"),  # must be ignored
            dry_run=True,
        )
        names = {name.lower() for _pid, name in game._candidates()}
        assert names.isdisjoint(_PROTECTED)


class TestMemoryOptimizer:
    """TestMemoryOptimizer."""
    def test_stats_shape(self):
        """test_stats_shape."""
        optimizer = MemoryOptimizer()
        stats = optimizer.get_system_ram_metrics()
        assert isinstance(stats, SystemRamMetrics)
        assert stats.total_bytes > 0
        assert 0 <= stats.percent_used <= 100

    @pytest.mark.skipif(not IS_WINDOWS, reason="trimming is Windows-only")
    def test_optimize_returns_result(self):
        """test_optimize_returns_result."""
        optimizer = MemoryOptimizer()
        result = optimizer.optimize_all_background_working_sets()
        assert isinstance(result, MemoryOptimizeResult)
        assert isinstance(result.processes_trimmed, int)
        assert isinstance(result.bytes_freed_estimate, int)
        assert isinstance(result.errors, list)

    def test_optimize_off_platform_no_crash(self):
        """test_optimize_off_platform_no_crash."""
        optimizer = MemoryOptimizer()
        result = optimizer.optimize_all_background_working_sets()
        assert isinstance(result, MemoryOptimizeResult)
