"""Tests for the read-only browser-extension auditor.

We build a fake Chromium/Firefox profile tree under a temp home so the scan is
deterministic and platform-independent.
"""

from __future__ import annotations

import json
import os
import platform

import pytest

from cortex_unified.system_tools.browser_extensions import (
    BrowserExtension,
    BrowserExtensionAuditor,
)

IS_WINDOWS = platform.system() == "Windows"


class TestPermissionRisk:
    """TestPermissionRisk."""
    def test_broad_permissions_flagged(self):
        """test_broad_permissions_flagged."""
        e = BrowserExtension("Chrome", "Spy", "1.0", "abc", ["<all_urls>", "tabs"])
        assert e.broad_permissions is True

    def test_narrow_permissions_not_flagged(self):
        """test_narrow_permissions_not_flagged."""
        e = BrowserExtension("Chrome", "Calc", "1.0", "abc", ["storage"])
        assert e.broad_permissions is False

    def test_to_dict_includes_flag(self):
        """test_to_dict_includes_flag."""
        e = BrowserExtension("Edge", "X", "2", "id", ["cookies"])
        d = e.to_dict()
        assert d["broad_permissions"] is True
        assert d["browser"] == "Edge"


def _make_chrome_ext(base, browser_parts, ext_id, manifest):
    """_make_chrome_ext."""
    ext_dir = base.joinpath(*browser_parts, "Default", "Extensions", ext_id, "1.0_0")
    ext_dir.mkdir(parents=True)
    (ext_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    # Point LOCALAPPDATA (Windows) or ~/.config (else) at tmp for Chromium.
    """fake_home."""
    if IS_WINDOWS:
        local = tmp_path / "AppData" / "Local"
        local.mkdir(parents=True)
        monkeypatch.setenv("LOCALAPPDATA", str(local))
    else:
        local = tmp_path / ".config"
        local.mkdir(parents=True)
    return tmp_path, local


class TestChromiumScan:
    """TestChromiumScan."""
    def test_finds_extension_with_permissions(self, fake_home):
        """test_finds_extension_with_permissions."""
        home, local = fake_home
        _make_chrome_ext(
            local, ["Google", "Chrome", "User Data"], "aaaabbbbccccdddd",
            {"name": "Ad Blocker", "version": "3.2", "permissions": ["tabs", "<all_urls>"]},
        )
        auditor = BrowserExtensionAuditor(home=home)
        exts = auditor.audit()
        chrome = [e for e in exts if e.browser == "Chrome"]
        assert len(chrome) == 1
        assert chrome[0].name == "Ad Blocker"
        assert chrome[0].version == "3.2"
        assert chrome[0].broad_permissions is True

    def test_host_permissions_merged(self, fake_home):
        """test_host_permissions_merged."""
        home, local = fake_home
        _make_chrome_ext(
            local, ["Microsoft", "Edge", "User Data"], "id2",
            {"name": "Tool", "version": "1", "host_permissions": ["*://*/*"]},
        )
        exts = BrowserExtensionAuditor(home=home).audit()
        edge = [e for e in exts if e.browser == "Edge"]
        assert edge and edge[0].broad_permissions is True

    def test_no_browsers_returns_empty(self, tmp_path, monkeypatch):
        """test_no_browsers_returns_empty."""
        if IS_WINDOWS:
            monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "empty"))
        auditor = BrowserExtensionAuditor(home=tmp_path / "nothing")
        assert auditor.audit() == []

    def test_bad_manifest_skipped(self, fake_home):
        """test_bad_manifest_skipped."""
        home, local = fake_home
        ext_dir = local.joinpath("Google", "Chrome", "User Data", "Default",
                                 "Extensions", "broken", "1.0_0")
        ext_dir.mkdir(parents=True)
        (ext_dir / "manifest.json").write_text("{ not valid json", encoding="utf-8")
        # Should not raise, just skip the broken one.
        exts = BrowserExtensionAuditor(home=home).audit()
        assert all(e.ext_id != "broken" for e in exts)


class TestAuditNeverRaises:
    """TestAuditNeverRaises."""
    def test_audit_returns_list(self):
        """test_audit_returns_list."""
        assert isinstance(BrowserExtensionAuditor().audit(), list)
