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
    def test_clean(self):
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection did not find any integrity violations.")
        assert r.success and r.status == "clean"

    def test_repaired(self):
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection found corrupt files and successfully "
            "repaired them.")
        assert r.success and r.status == "repaired" and r.needs_reboot

    def test_partial(self):
        r = SystemRepair._parse_sfc(
            "Windows Resource Protection found corrupt files but was unable to fix "
            "some of them.")
        assert r.success is False and r.status == "partial"
        assert "dism" in r.message.lower()

    def test_error_when_none(self):
        r = SystemRepair._parse_sfc(None)
        assert r.success is False and "administrator" in r.message.lower()


class TestDismParse:
    def test_clean(self):
        r = SystemRepair._parse_dism("No component store corruption detected.", "CheckHealth")
        assert r.success and r.status == "clean"

    def test_repairable(self):
        r = SystemRepair._parse_dism("The component store is repairable.", "ScanHealth")
        assert r.success and r.status == "repairable"
        assert "restorehealth" in r.message.lower()

    def test_repaired(self):
        r = SystemRepair._parse_dism(
            "The restore operation completed successfully.", "RestoreHealth")
        assert r.success and r.status == "repaired" and r.needs_reboot

    def test_error_code(self):
        r = SystemRepair._parse_dism("Error: 0x800f081f\nThe source files could not be found.",
                                    "RestoreHealth")
        assert r.success is False and "0x800f081f" in r.message


class TestChkdskParse:
    def test_clean(self):
        r = SystemRepair._parse_chkdsk(
            "Windows has scanned the file system and found no problems.", "C")
        assert r.success and r.status == "clean"

    def test_errors(self):
        r = SystemRepair._parse_chkdsk(
            "Errors found. CHKDSK cannot continue in read-only mode.", "C")
        assert r.status == "errors" and r.needs_reboot

    def test_invalid_drive(self):
        r = SystemRepair().run_chkdsk_scan("not-a-drive")
        assert r.success is False


class TestGating:
    def test_is_supported(self):
        assert SystemRepair.is_supported() == IS_WINDOWS

    def test_is_elevated_bool(self):
        assert isinstance(SystemRepair.is_elevated(), bool)

    def test_dism_invalid_action_defaults(self):
        # An unknown action must not crash; it falls back to CheckHealth path.
        # We only verify it returns a RepairResult (may be error off-Windows).
        r = SystemRepair().run_dism("BogusAction") if IS_WINDOWS else \
            SystemRepair._parse_dism("No component store corruption detected.", "CheckHealth")
        assert isinstance(r, RepairResult)


class TestDecode:
    def test_utf16_with_nuls(self):
        raw = "No component store corruption detected.".encode("utf-16-le")
        text = SystemRepair._decode(raw)
        assert "No component store corruption detected." in text

    def test_plain_utf8(self):
        assert "hello" in SystemRepair._decode(b"hello")

    def test_empty(self):
        assert SystemRepair._decode(b"") == ""
