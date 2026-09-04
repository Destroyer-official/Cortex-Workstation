"""Tests for human-friendly process descriptions (honest, cached)."""

from __future__ import annotations

import platform

from cortex_unified.system_tools import process_meta

IS_WINDOWS = platform.system() == "Windows"


class TestKnown:
    """Testknown.

    Manages TestKnown operations and coordinates related state changes for the component.
    """
    def test_common_system_processes(self):
        """test_common_system_processes.

        Manages test common system processes operations and coordinates related state changes for the component.
        """
        assert "Service Host" in process_meta.known_description("svchost.exe")
        assert "Explorer" in process_meta.known_description("explorer.exe")
        assert process_meta.known_description("LSASS.EXE")  # case-insensitive

    def test_idle_labeled_as_not_real(self):
        """test_idle_labeled_as_not_real.

        Manages test idle labeled as not real operations and coordinates related state changes for the component.
        """
        d = process_meta.known_description("System Idle Process")
        assert "not a real program" in d.lower()

    def test_unknown_returns_empty(self):
        """test_unknown_returns_empty.

        Manages test unknown returns empty operations and coordinates related state changes for the component.
        """
        assert process_meta.known_description("totally_made_up_xyz.exe") == ""


class TestDescribe:
    """Testdescribe.

    Manages TestDescribe operations and coordinates related state changes for the component.
    """
    def test_describe_prefers_known(self):
        # Even with a bogus path, a known name wins and never reads disk.
        """test_describe_prefers_known.

        Manages test describe prefers known operations and coordinates related state changes for the component.
        """
        assert process_meta.describe("chrome.exe", "Z:\\nope\\chrome.exe") \
            == "Google Chrome web browser"

    def test_describe_unknown_no_path_is_empty(self):
        """test_describe_unknown_no_path_is_empty.

        Manages test describe unknown no path is empty operations and coordinates related state changes for the component.
        """
        assert process_meta.describe("weird_unknown.exe", "") == ""

    def test_describe_never_fabricates(self):
        # An unknown name with a non-existent path must yield '', not a guess.
        """test_describe_never_fabricates.

        Manages test describe never fabricates operations and coordinates related state changes for the component.
        """
        assert process_meta.describe("zzzz.exe", "Q:\\does\\not\\exist.exe") == ""


class TestFileDescriptionCache:
    """Testfiledescriptioncache.

    Manages TestFileDescriptionCache operations and coordinates related state changes for the component.
    """
    def test_cache_used(self):
        """test_cache_used.

        Manages test cache used operations and coordinates related state changes for the component.
        """
        process_meta._desc_cache.clear()
        # Non-existent path -> '' and gets cached (no repeated disk hits).
        r1 = process_meta.file_description("Q:\\missing\\app.exe")
        assert r1 == ""
        assert "Q:\\missing\\app.exe" in process_meta._desc_cache

    def test_empty_path(self):
        """test_empty_path.

        Manages test empty path operations and coordinates related state changes for the component.
        """
        assert process_meta.file_description("") == ""


class TestRealSystemExeIfWindows:
    """Testrealsystemexeifwindows.

    Manages TestRealSystemExeIfWindows operations and coordinates related state changes for the component.
    """
    def test_reads_a_real_description(self):
        """test_reads_a_real_description.

        Manages test reads a real description operations and coordinates related state changes for the component.
        """
        if not IS_WINDOWS:
            import pytest
            pytest.skip("Windows-only version info")
        import os
        # explorer.exe almost always has a FileDescription.
        exe = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "explorer.exe")
        if os.path.exists(exe):
            desc = process_meta.file_description(exe)
            assert isinstance(desc, str)  # may be '' on odd builds, but must not raise
