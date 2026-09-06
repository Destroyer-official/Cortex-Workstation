"""Tests for the Windows restore-point safety module.

These avoid actually creating a restore point (that needs admin and modifies
the system). We test the honest status parsing, capability checks, and the
read-only listing path.
"""

from __future__ import annotations

import platform

from cortex_unified.system_tools.restore_point import (
    RestorePointManager,
    RestorePointResult,
    RestoreStatus,
)

IS_WINDOWS = platform.system() == "Windows"


class TestResultSemantics:
    """Group testresultsemantics tests covering created flags; throttled is ok to proceed; disabled and not elevated block proceed; to dict."""
    def test_created_flags(self):
        """Verify created flags via RestorePointResult."""
        r = RestorePointResult(RestoreStatus.CREATED)
        assert r.created is True
        assert r.ok_to_proceed is True

    def test_throttled_is_ok_to_proceed(self):
        # A recent point already exists -> safe to proceed.
        """Verify throttled is ok to proceed via RestorePointResult."""
        r = RestorePointResult(RestoreStatus.THROTTLED)
        assert r.created is False
        assert r.ok_to_proceed is True

    def test_disabled_and_not_elevated_block_proceed(self):
        """Verify disabled and not elevated block proceed via RestorePointResult."""
        assert RestorePointResult(RestoreStatus.PROTECTION_DISABLED).ok_to_proceed is False
        assert RestorePointResult(RestoreStatus.NOT_ELEVATED).ok_to_proceed is False
        assert RestorePointResult(RestoreStatus.FAILED).ok_to_proceed is False

    def test_to_dict(self):
        """Verify to dict via RestorePointResult, to_dict."""
        d = RestorePointResult(RestoreStatus.CREATED, "ok").to_dict()
        assert d == {"status": "created", "message": "ok", "created": True}


class TestOutputParsing:
    """Group testoutputparsing tests covering parse created; parse throttled; parse protection disabled; parse failed with message; parse empty is failed; parse garbage is failed."""
    def test_parse_created(self):
        """Verify parse created via RestorePointManager._parse_create_output."""
        r = RestorePointManager._parse_create_output("STATUS=CREATED\n")
        assert r.status is RestoreStatus.CREATED

    def test_parse_throttled(self):
        """Verify parse throttled via RestorePointManager._parse_create_output."""
        r = RestorePointManager._parse_create_output("STATUS=THROTTLED")
        assert r.status is RestoreStatus.THROTTLED

    def test_parse_protection_disabled(self):
        """Verify parse protection disabled via RestorePointManager._parse_create_output."""
        r = RestorePointManager._parse_create_output("STATUS=PROTECTION_DISABLED")
        assert r.status is RestoreStatus.PROTECTION_DISABLED

    def test_parse_failed_with_message(self):
        """Verify parse failed with message via RestorePointManager._parse_create_output."""
        r = RestorePointManager._parse_create_output("STATUS=FAILED;MSG=boom happened")
        assert r.status is RestoreStatus.FAILED
        assert "boom happened" in r.message

    def test_parse_empty_is_failed(self):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.
        """
        assert RestorePointManager._parse_create_output(None).status is RestoreStatus.FAILED
        assert RestorePointManager._parse_create_output("").status is RestoreStatus.FAILED

    def test_parse_garbage_is_failed(self):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.
        """
        assert RestorePointManager._parse_create_output("hello world").status is RestoreStatus.FAILED


class TestWmiTimeParsing:
    """Group testwmitimeparsing tests covering wmi datetime; empty; passthrough non wmi."""
    def test_wmi_datetime(self):
        """Verify wmi datetime via RestorePointManager._parse_wmi_time."""
        assert RestorePointManager._parse_wmi_time("20240115093000.000000-000") == "2024-01-15 09:30:00"

    def test_empty(self):
        """Verify empty via RestorePointManager._parse_wmi_time."""
        assert RestorePointManager._parse_wmi_time(None) == ""
        assert RestorePointManager._parse_wmi_time("") == ""

    def test_passthrough_non_wmi(self):
        """Verify passthrough non wmi via RestorePointManager._parse_wmi_time."""
        assert RestorePointManager._parse_wmi_time("2024-01-15") == "2024-01-15"


class TestCapabilities:
    """Group testcapabilities tests covering is supported matches platform; is elevated returns bool; list points returns list; create non windows is not supported; create without admin reports not elevated."""
    def test_is_supported_matches_platform(self):
        """Verify is supported matches platform via RestorePointManager.is_supported."""
        assert RestorePointManager.is_supported() == IS_WINDOWS

    def test_is_elevated_returns_bool(self):
        """Verify is elevated returns bool via RestorePointManager.is_elevated."""
        assert isinstance(RestorePointManager.is_elevated(), bool)

    def test_list_points_returns_list(self):
        # Read-only; must never raise regardless of platform/protection state.
        """Verify list points returns list via RestorePointManager, list_points."""
        assert isinstance(RestorePointManager().list_points(), list)

    def test_create_non_windows_is_not_supported(self):
        """Verify create non windows is not supported via pytest.skip, RestorePointManager, create."""
        if IS_WINDOWS:
            import pytest
            pytest.skip("covered by the elevation path on Windows")
        r = RestorePointManager().create("test")
        assert r.status is RestoreStatus.NOT_SUPPORTED

    def test_create_without_admin_reports_not_elevated(self):
        """Verify create without admin reports not elevated via RestorePointManager, mgr.create, mgr.is_elevated."""
        mgr = RestorePointManager()
        if not IS_WINDOWS or mgr.is_elevated():
            import pytest
            pytest.skip("only meaningful on Windows when NOT elevated")
        # Non-admin: must refuse honestly, never claim success, no side effects.
        r = mgr.create("Cortex test")
        assert r.status is RestoreStatus.NOT_ELEVATED
        assert r.created is False
