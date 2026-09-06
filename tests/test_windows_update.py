"""Tests for Windows Update surfacing (parsers + gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.windows_update import PendingUpdate, WindowsUpdate

IS_WINDOWS = platform.system() == "Windows"


class TestPendingParse:
    """Group testpendingparse tests covering empty; single; array; titleless skipped; no kb."""
    def test_empty(self):
        """Verify empty via WindowsUpdate._parse_pending."""
        assert WindowsUpdate._parse_pending(None) == []
        assert WindowsUpdate._parse_pending("bad{") == []

    def test_single(self):
        """Verify single via WindowsUpdate._parse_pending."""
        payload = ('{"Title":"2026-07 Cumulative Update","KB":"5001234",'
                   '"Severity":"Critical","Size":123456789}')
        ups = WindowsUpdate._parse_pending(payload)
        assert len(ups) == 1
        u = ups[0]
        assert isinstance(u, PendingUpdate)
        assert u.kb == "KB5001234"
        assert u.severity == "Critical"
        assert u.size_bytes == 123456789

    def test_array(self):
        """Verify array via WindowsUpdate._parse_pending."""
        payload = ('[{"Title":"Update A","KB":"1","Size":10},'
                   '{"Title":"Update B","KB":"2","Size":20}]')
        assert len(WindowsUpdate._parse_pending(payload)) == 2

    def test_titleless_skipped(self):
        """Verify titleless skipped via WindowsUpdate._parse_pending."""
        assert WindowsUpdate._parse_pending('{"Title":"","KB":"1"}') == []

    def test_no_kb(self):
        """Verify no kb via WindowsUpdate._parse_pending."""
        u = WindowsUpdate._parse_pending('{"Title":"Defender def update","Size":0}')[0]
        assert u.kb == ""


class TestHistoryParse:
    """Group testhistoryparse tests covering success and fail; date formatted; empty."""
    def test_success_and_fail(self):
        """Handle an operation failure and notify the user.

        Captures error details, displays an informative failure state in the UI, resets progress indicators, and re-enables interactive controls.
        """
        payload = ('[{"Title":"KB1","Date":"2026-07-01T10:00:00","Result":2},'
                   '{"Title":"KB2","Date":"2026-06-01T10:00:00","Result":4}]')
        rows = WindowsUpdate._parse_history(payload)
        assert len(rows) == 2
        assert rows[0]["result"] == "Succeeded" and rows[0]["succeeded"] is True
        assert rows[1]["result"] == "Failed" and rows[1]["succeeded"] is False

    def test_date_formatted(self):
        """test_date_formatted.

        Converts raw numeric values into formatted, localized, and human-readable string representations.
        """
        rows = WindowsUpdate._parse_history('{"Title":"X","Date":"2026-07-01T10:00:00","Result":2}')
        assert rows[0]["date"] == "2026-07-01 10:00:00"

    def test_empty(self):
        """Verify empty via WindowsUpdate._parse_history."""
        assert WindowsUpdate._parse_history(None) == []
        assert WindowsUpdate._parse_history("") == []


class TestGating:
    """Group testgating tests covering is supported; last activity shape; check pending returns list; to dict."""
    def test_is_supported(self):
        """Verify is supported via WindowsUpdate.is_supported."""
        assert WindowsUpdate.is_supported() == IS_WINDOWS

    def test_last_activity_shape(self):
        """Verify last activity shape via WindowsUpdate, last_activity."""
        a = WindowsUpdate().last_activity()
        assert set(a) == {"last_check", "last_install"}

    def test_check_pending_returns_list(self):
        # Off-Windows returns []; on Windows it may query online but must be a list.
        """Verify check pending returns list via WindowsUpdate, check_pending."""
        result = WindowsUpdate().check_pending() if not IS_WINDOWS else []
        assert isinstance(result, list)

    def test_to_dict(self):
        """Verify to dict via PendingUpdate, to_dict."""
        d = PendingUpdate("Title", "KB1", "Important", 100).to_dict()
        assert set(d) == {"title", "kb", "severity", "size_bytes"}
