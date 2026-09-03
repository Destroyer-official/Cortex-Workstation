"""Tests for the power-plan tuner (parsing + safety gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.performance_tuner import PerformanceTuner, PowerPlan

IS_WINDOWS = platform.system() == "Windows"

SAMPLE = (
    "\r\nExisting Power Schemes (* Active)\r\n"
    "-----------------------------------\r\n"
    "Power Scheme GUID: 381b4222-f694-41f0-9685-ff5bb260df2e  (Balanced) *\r\n"
    "Power Scheme GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c  (High performance)\r\n"
    "Power Scheme GUID: a1841308-3541-4fab-bc81-f71556f20b4a  (Power saver)\r\n"
)


class TestParse:
    """TestParse."""
    def test_parses_all_plans(self):
        """test_parses_all_plans."""
        plans = PerformanceTuner._parse(SAMPLE)
        assert len(plans) == 3
        assert all(isinstance(p, PowerPlan) for p in plans)
        names = {p.name for p in plans}
        assert "Balanced" in names and "High performance" in names

    def test_marks_active_plan(self):
        """test_marks_active_plan."""
        plans = PerformanceTuner._parse(SAMPLE)
        active = [p for p in plans if p.active]
        assert len(active) == 1
        assert active[0].name == "Balanced"
        assert active[0].guid == "381b4222-f694-41f0-9685-ff5bb260df2e"

    def test_empty_input(self):
        """test_empty_input."""
        assert PerformanceTuner._parse(None) == []
        assert PerformanceTuner._parse("") == []


class TestSafety:
    """TestSafety."""
    def test_is_supported_matches_platform(self):
        """test_is_supported_matches_platform."""
        assert PerformanceTuner.is_supported() == IS_WINDOWS

    def test_set_active_rejects_bad_guid(self):
        """test_set_active_rejects_bad_guid."""
        ok, msg = PerformanceTuner().set_active("not-a-guid")
        assert ok is False

    def test_list_plans_returns_list(self):
        """test_list_plans_returns_list."""
        assert isinstance(PerformanceTuner().list_plans(), list)

    def test_to_dict(self):
        """test_to_dict."""
        p = PowerPlan(guid="g", name="Balanced", active=True)
        assert p.to_dict() == {"guid": "g", "name": "Balanced", "active": True}
