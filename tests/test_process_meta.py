"""Tests for human-friendly process descriptions (honest, cached)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools import process_meta

IS_WINDOWS = platform.system() == "Windows"


class TestKnown:
    """Group testknown tests covering common system processes; idle labeled as not real; unknown returns empty."""
    def test_common_system_processes(self):
        """Verify common system processes via process_meta.known_description."""
        assert "Service Host" in process_meta.known_description("svchost.exe")
        assert "Explorer" in process_meta.known_description("explorer.exe")
        assert process_meta.known_description("LSASS.EXE")  # case-insensitive

    def test_idle_labeled_as_not_real(self):
        """Verify idle labeled as not real via process_meta.known_description, d.lower."""
        d = process_meta.known_description("System Idle Process")
        assert "not a real program" in d.lower()

    def test_unknown_returns_empty(self):
        """Verify unknown returns empty via process_meta.known_description."""
        assert process_meta.known_description("totally_made_up_xyz.exe") == ""


class TestDescribe:
    """Group testdescribe tests covering describe prefers known; describe unknown no path is empty; describe never fabricates."""
    def test_describe_prefers_known(self):
        # Even with a bogus path, a known name wins and never reads disk.
        """Verify describe prefers known via process_meta.describe."""
        assert process_meta.describe("chrome.exe", "Z:\\nope\\chrome.exe") \
            == "Google Chrome web browser"

    def test_describe_unknown_no_path_is_empty(self):
        """Verify describe unknown no path is empty via process_meta.describe."""
        assert process_meta.describe("weird_unknown.exe", "") == ""

    def test_describe_never_fabricates(self):
        # An unknown name with a non-existent path must yield '', not a guess.
        """Verify describe never fabricates via process_meta.describe."""
        assert process_meta.describe("zzzz.exe", "Q:\\does\\not\\exist.exe") == ""


class TestFileDescriptionCache:
    """Group testfiledescriptioncache tests covering cache used; empty path."""
    def test_cache_used(self):
        """Verify cache used via process_meta._desc_cache.clear, process_meta.file_description."""
        process_meta._desc_cache.clear()
        # Non-existent path -> '' and gets cached (no repeated disk hits).
        r1 = process_meta.file_description("Q:\\missing\\app.exe")
        assert r1 == ""
        assert "Q:\\missing\\app.exe" in process_meta._desc_cache

    def test_empty_path(self):
        """Verify empty path via process_meta.file_description."""
        assert process_meta.file_description("") == ""


class TestRealSystemExeIfWindows:
    """Group testrealsystemexeifwindows tests covering reads a real description."""
    def test_reads_a_real_description(self):
        """Verify reads a real description via os.path.join, pytest.skip, os.environ.get."""
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only version info")
        import os
        # explorer.exe almost always has a FileDescription.
        exe = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "explorer.exe")
        if os.path.exists(exe):
            desc = process_meta.file_description(exe)
            assert isinstance(desc, str)  # may be '' on odd builds, but must not raise
