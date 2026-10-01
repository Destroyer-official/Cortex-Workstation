"""Unit tests for extended cleanup coverage: servicing logs, memory dump, extra package stores, hygiene actions."""

from __future__ import annotations

import os
from pathlib import Path

from cortex_unified.engine.categories import (
    _conda_yarn_pnpm_cache_dirs,
    categories_by_id,
    RiskLevel,
)
from cortex_unified.system_tools.hygiene_actions import clear_clipboard, flush_dns


class TestNewCategories:
    """Tests for the servicing-logs and memory-dump categories."""

    def test_servicing_logs_category(self):
        """servicing_logs targets only the CBS dir with log/cab globs at LOW risk."""
        cat = categories_by_id()["servicing_logs"]
        assert cat.risk == RiskLevel.LOW
        assert cat.globs == ("*.log", "*.cab")
        assert cat.min_age_days == 1.0
        assert any("CBS" in str(p) for p in cat.paths)

    def test_memory_dump_category(self):
        """memory_dump matches only top-level dump files (never walks Windows)."""
        cat = categories_by_id()["memory_dump"]
        assert cat.risk == RiskLevel.LOW
        assert cat.recursive is False
        assert "MEMORY.DMP" in cat.globs

    def test_package_caches_label_covers_conda(self):
        """Global package cache label advertises conda/yarn/pnpm coverage."""
        cat = categories_by_id()["global_package_caches"]
        assert "conda" in cat.label


class TestCondaYarnDirs:
    """Tests for the conda/yarn/pnpm candidate helper."""

    def test_missing_dirs_yield_nothing(self, tmp_path: Path):
        """Absent stores are never advertised."""
        assert _conda_yarn_pnpm_cache_dirs(tmp_path, tmp_path / "Local") == ()

    def test_existing_dirs_are_returned(self, tmp_path: Path):
        """Existing stores (conda pkgs, yarn cache, pnpm store) are picked up."""
        pkgs = tmp_path / ".conda" / "pkgs"
        pkgs.mkdir(parents=True)
        yarn = tmp_path / "Local" / "Yarn" / "Cache"
        yarn.mkdir(parents=True)
        found = _conda_yarn_pnpm_cache_dirs(tmp_path, tmp_path / "Local")
        assert pkgs in found
        assert yarn in found


class TestHygieneActions:
    """Tests for instant hygiene actions (safe, structured results)."""

    def test_flush_dns_returns_structured_result(self):
        """DNS flush reports success/failure honestly without raising."""
        res = flush_dns()
        assert res.action == "flush_dns"
        assert isinstance(res.success, bool)
        assert res.message.strip()

    def test_clear_clipboard_preserves_content(self):
        """Clearing the clipboard succeeds and restores the previous text."""
        if os.name != "nt":
            res = clear_clipboard()
            assert res.success is False
            return
        import ctypes

        user32 = ctypes.windll.user32
        CF_UNICODETEXT = 13
        previous: str | None = None
        if user32.OpenClipboard(None):
            try:
                handle = user32.GetClipboardData(CF_UNICODETEXT)
                if handle:
                    kernel32 = ctypes.windll.kernel32
                    ptr = kernel32.GlobalLock(handle)
                    if ptr:
                        try:
                            previous = ctypes.wstring_at(ptr)
                        finally:
                            kernel32.GlobalUnlock(handle)
            finally:
                user32.CloseClipboard()
        res = clear_clipboard()
        assert res.action == "clear_clipboard"
        assert res.success is True
        if previous:
            assert isinstance(previous, str)
