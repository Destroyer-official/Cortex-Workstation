"""Tests for the release infrastructure helpers.

Covers the informational update checker (version parsing, comparison,
offline tolerance) and the crash-report writer installed by the premium
app's excepthook.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


class TestParseVersion:
    def test_plain_and_v_prefixed(self):
        from cortex_unified.system_tools.update_checker import parse_version
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("v1.2.3") == (1, 2, 3)
        assert parse_version("  v10.0.13 ") == (10, 0, 13)

    @pytest.mark.parametrize("bad", ["", "abc", "1.2", "v1.2.3.4",
                                     "release-42"])
    def test_unparseable_tags_return_none(self, bad):
        from cortex_unified.system_tools.update_checker import parse_version
        assert parse_version(bad) is None


class TestCheckForUpdate:
    def _patch_fetch(self, monkeypatch, tag):
        from cortex_unified.system_tools import update_checker as uc
        monkeypatch.setattr(uc, "fetch_latest_tag",
                            lambda *a, **k: tag)

    def test_update_available_when_latest_is_newer(self, monkeypatch):
        from cortex_unified.system_tools.update_checker import check_for_update
        self._patch_fetch(monkeypatch, "v9.9.9")
        result = check_for_update(installed="1.0.0")
        assert result["status"] == "update_available"
        assert result["latest"] == "v9.9.9"
        assert result["installed"] == "1.0.0"

    def test_up_to_date_when_equal_or_older(self, monkeypatch):
        from cortex_unified.system_tools.update_checker import check_for_update
        self._patch_fetch(monkeypatch, "v1.0.0")
        assert check_for_update(installed="1.0.0")["status"] == "up_to_date"
        self._patch_fetch(monkeypatch, "v0.9.1")
        assert check_for_update(installed="1.0.0")["status"] == "up_to_date"

    def test_offline_reports_unknown_never_raises(self, monkeypatch):
        from cortex_unified.system_tools.update_checker import check_for_update
        self._patch_fetch(monkeypatch, None)
        result = check_for_update(installed="1.0.0")
        assert result["status"] == "unknown"

    def test_unparseable_remote_tag_is_unknown(self, monkeypatch):
        from cortex_unified.system_tools.update_checker import check_for_update
        self._patch_fetch(monkeypatch, "not-a-version")
        assert check_for_update(installed="1.0.0")["status"] == "unknown"


class TestCrashReport:
    def test_excepthook_writes_crash_file(self, tmp_path, monkeypatch):
        """The excepthook persists a redact-flagged crash report file."""
        import cortex_unified.ui.premium.app as app_mod

        monkeypatch.setattr(app_mod, "log_dir", lambda: tmp_path / "logs")
        captured = []
        monkeypatch.setattr(sys, "__excepthook__",
                            lambda *a: captured.append(a))

        app_mod._install_excepthook()
        try:
            raise ValueError("boom-for-test")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()
            sys.excepthook(exc_type, exc_value, exc_tb)

        reports = list((tmp_path / "logs").glob("crash_*.txt"))
        assert len(reports) == 1
        text = reports[0].read_text(encoding="utf-8")
        assert "boom-for-test" in text
        assert "personal filenames" in text   # privacy flag present
        assert len(captured) == 1             # default hook still chained
