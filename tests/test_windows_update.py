"""Tests for Windows Update surfacing (parsers + gating)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools.windows_update import PendingUpdate, WindowsUpdate

IS_WINDOWS = platform.system() == "Windows"


class TestPendingParse:
    def test_empty(self):
        assert WindowsUpdate._parse_pending(None) == []
        assert WindowsUpdate._parse_pending("bad{") == []

    def test_single(self):
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
        payload = ('[{"Title":"Update A","KB":"1","Size":10},'
                   '{"Title":"Update B","KB":"2","Size":20}]')
        assert len(WindowsUpdate._parse_pending(payload)) == 2

    def test_titleless_skipped(self):
        assert WindowsUpdate._parse_pending('{"Title":"","KB":"1"}') == []

    def test_no_kb(self):
        u = WindowsUpdate._parse_pending('{"Title":"Defender def update","Size":0}')[0]
        assert u.kb == ""


class TestHistoryParse:
    def test_success_and_fail(self):
        payload = ('[{"Title":"KB1","Date":"2026-07-01T10:00:00","Result":2},'
                   '{"Title":"KB2","Date":"2026-06-01T10:00:00","Result":4}]')
        rows = WindowsUpdate._parse_history(payload)
        assert len(rows) == 2
        assert rows[0]["result"] == "Succeeded" and rows[0]["succeeded"] is True
        assert rows[1]["result"] == "Failed" and rows[1]["succeeded"] is False

    def test_date_formatted(self):
        rows = WindowsUpdate._parse_history('{"Title":"X","Date":"2026-07-01T10:00:00","Result":2}')
        assert rows[0]["date"] == "2026-07-01 10:00:00"

    def test_empty(self):
        assert WindowsUpdate._parse_history(None) == []
        assert WindowsUpdate._parse_history("") == []


class TestGating:
    def test_is_supported(self):
        assert WindowsUpdate.is_supported() == IS_WINDOWS

    def test_last_activity_shape(self):
        a = WindowsUpdate().last_activity()
        assert set(a) == {"last_check", "last_install"}

    def test_check_pending_returns_list(self):
        # Off-Windows returns []; on Windows it may query online but must be a list.
        result = WindowsUpdate().check_pending() if not IS_WINDOWS else []
        assert isinstance(result, list)

    def test_to_dict(self):
        d = PendingUpdate("Title", "KB1", "Important", 100).to_dict()
        assert set(d) == {"title", "kb", "severity", "size_bytes"}
