"""Tests for the SFC/DISM/CHKDSK repair orchestrator (parsers + gating).

We never actually run sfc/dism/chkdsk here - they take many minutes and modify
the system. We test the result interpretation (the important part) with real
sample output strings, plus platform gating and input validation.
"""

from __future__ import annotations

import platform

from cortex_unified.system_tools.system_repair import RepairResult, SystemRepair

IS_WINDOWS = platform.system() == "Windows"


class TestSfcParse:
    """TestSfcParse."""
    def test_clean(self):
        """test_clean."""
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection did not find any integrity violations.")
        assert r.success and r.status == "clean"

    def test_repaired(self):
        """test_repaired."""
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection found corrupt files and successfully "
            "repaired them.")
        assert r.success and r.status == "repaired" and r.needs_reboot

    def test_partial(self):
        """test_partial."""
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection found corrupt files but was unable to fix "
            "some of them.")
        assert r.success is False and r.status == "partial"
        assert "dism" in r.message.lower()

    def test_error_when_none(self):
        """test_error_when_none."""
        r = SystemRepair._parse_sfc(None)
        assert r.success is False and "administrator" in r.message.lower()


class TestDismParse:
    """TestDismParse."""
    def test_clean(self):
        """test_clean."""
        r = SystemRepair._parse_dism("No component store corruption detected.", "CheckHealth")
        assert r.success and r.status == "clean"

    def test_repairable(self):
        """test_repairable."""
        r = SystemRepair._parse_dism("The component store is repairable.", "ScanHealth")
        assert r.success and r.status == "repairable"
        assert "restorehealth" in r.message.lower()

    def test_repaired(self):
        """test_repaired."""
        r = SystemRepair._parse_dism(
            "The restore operation completed successfully.", "RestoreHealth")
        assert r.success and r.status == "repaired" and r.needs_reboot

    def test_error_code(self):
        """test_error_code."""
        r = SystemRepair._parse_dism("Error: 0x800f081f\nThe source files could not be found.",
                                    "RestoreHealth")
        assert r.success is False and "0x800f081f" in r.message


class TestChkdskParse:
    """TestChkdskParse."""
    def test_clean(self):
        """test_clean."""
        r = SystemRepair._parse_chkdsk(
            "Windows has scanned the file system and found no problems.", "C")
        assert r.success and r.status == "clean"

    def test_errors(self):
        """test_errors."""
        r = SystemRepair._parse_chkdsk(
            "Errors found. CHKDSK cannot continue in read-only mode.", "C")
        assert r.status == "errors" and r.needs_reboot

    def test_invalid_drive(self):
        """test_invalid_drive."""
        r = SystemRepair().run_chkdsk_scan("not-a-drive")
        assert r.success is False


class TestGating:
    """TestGating."""
    def test_is_supported(self):
        """test_is_supported."""
        assert SystemRepair.is_supported() == IS_WINDOWS

    def test_is_elevated_bool(self):
        """test_is_elevated_bool."""
        assert isinstance(SystemRepair.is_elevated(), bool)

    def test_dism_invalid_action_defaults(self):
        # An unknown action must not crash; it falls back to CheckHealth path.
        # We only verify it returns a RepairResult (may be error off-Windows).
        """test_dism_invalid_action_defaults."""
        r = SystemRepair().run_dism("BogusAction") if IS_WINDOWS else \
            SystemRepair._parse_dism("No component store corruption detected.", "CheckHealth")
        assert isinstance(r, RepairResult)


class TestDecode:
    """TestDecode."""
    def test_utf16_with_nuls(self):
        """test_utf16_with_nuls."""
        raw = "No component store corruption detected.".encode("utf-16-le")
        text = SystemRepair._decode(raw)
        assert "No component store corruption detected." in text

    def test_plain_utf8(self):
        """test_plain_utf8."""
        assert "hello" in SystemRepair._decode(b"hello")

    def test_empty(self):
        """test_empty."""
        assert SystemRepair._decode(b"") == ""
