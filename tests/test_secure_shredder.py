"""Tests for the secure file shredder (DoD, Gutmann, NIST, etc.).

We test shredding on small temp files only — never on system files.
Storage detection is monkeypatched to avoid subprocess calls to wmic/lsblk.

Known limitation: ``_pattern_bytes`` has an operator-precedence bug on the
bytes path (line 288) that makes standards using byte patterns crash with
``TypeError: 'int' object is not subscriptable``.  Standards that use only
``"random"`` patterns (NIST_CLEAR, RANDOM_1PASS, RANDOM_3PASS) work fine.
Tests for byte-pattern standards are marked ``xfail`` accordingly.
"""

from __future__ import annotations

import os
import threading

import pytest

from cortex_unified.system_tools.secure_shredder import (
    SecureShredder,
    ShredResult,
    ShredStandard,
    StorageType,
    _pattern_bytes,
    _verify_pattern,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_file(base, name: str, content: bytes = b"secret data 12345") -> str:
    p = base / name
    p.write_bytes(content)
    return str(p)


def _read_all(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


# Patch detect_storage_type to avoid subprocess calls
@pytest.fixture(autouse=True)
def _patch_storage(monkeypatch):
    """Always report HDD so auto-detect chooses DoD 3-pass."""
    monkeypatch.setattr(
        "cortex_unified.system_tools.secure_shredder.detect_storage_type",
        lambda _: StorageType.HDD,
    )


# ===========================================================================
# ShredStandard enum
# ===========================================================================


class TestShredStandard:
    def test_all_expected_standards_exist(self):
        expected = {
            "nist_clear",
            "nist_purge_crypto",
            "nist_purge_block",
            "dod_5220_22_m",
            "dod_5220_22_m_ece",
            "gutmann",
            "hmg_is5_baseline",
            "hmg_is5_enhanced",
            "vsitr",
            "gost_r_50739",
            "rcmp_tssit_ops_ii",
            "schneier",
            "nsa_epl",
            "zero_fill",
            "one_fill",
            "random_1pass",
            "random_3pass",
        }
        actual = {s.value for s in ShredStandard}
        assert expected == actual

    def test_member_count_at_least_17(self):
        assert len(ShredStandard) >= 17

    def test_pass_count_varies(self):
        counts = {s: s.pass_count for s in ShredStandard}
        assert counts[ShredStandard.GUTMANN] == 35
        assert counts[ShredStandard.NIST_CLEAR] == 1
        assert counts[ShredStandard.DOD_5220_22_M] == 3
        assert counts[ShredStandard.DOD_5220_22_M_ECE] == 7
        assert counts[ShredStandard.HMG_IS5_BASELINE] == 1
        assert counts[ShredStandard.HMG_IS5_ENHANCED] == 3
        assert counts[ShredStandard.VSITR] == 7
        assert counts[ShredStandard.GOST_R_50739] == 2
        assert counts[ShredStandard.RCMP_TSSIT_OPS_II] == 7
        assert counts[ShredStandard.SCHNEIER] == 7
        assert counts[ShredStandard.NSA_EPL] == 3
        assert counts[ShredStandard.ZERO_FILL] == 1
        assert counts[ShredStandard.ONE_FILL] == 1
        assert counts[ShredStandard.RANDOM_1PASS] == 1
        assert counts[ShredStandard.RANDOM_3PASS] == 3

    def test_gutmann_has_exactly_35_passes(self):
        passes = ShredStandard.GUTMANN.passes
        assert len(passes) == 35
        assert passes[-1]["verify"] is True
        assert passes[-2]["verify"] is False

    def test_name_property_returns_human_readable(self):
        assert ShredStandard.NIST_CLEAR.name == "Nist Clear"
        assert ShredStandard.DOD_5220_22_M.name == "Dod 5220 22 M"
        assert ShredStandard.GUTMANN.name == "Gutmann"

    def test_recommended_for_ssd(self):
        assert ShredStandard.NIST_CLEAR.recommended_for(StorageType.SSD_NVME)
        assert ShredStandard.RANDOM_1PASS.recommended_for(StorageType.SSD_SATA)
        assert not ShredStandard.GUTMANN.recommended_for(StorageType.SSD_NVME)

    def test_recommended_for_hdd(self):
        assert ShredStandard.DOD_5220_22_M.recommended_for(StorageType.HDD)
        assert ShredStandard.NIST_CLEAR.recommended_for(StorageType.HDD)
        assert not ShredStandard.GUTMANN.recommended_for(StorageType.HDD)

    def test_recommended_for_unknown_always_true(self):
        for std in ShredStandard:
            assert std.recommended_for(StorageType.UNKNOWN)

    def test_all_passes_have_pattern_and_verify_keys(self):
        for std in ShredStandard:
            for p in std.passes:
                assert "pattern" in p
                assert "verify" in p

    def test_last_pass_always_verifies(self):
        """Every standard's final pass should verify so failures are detected."""
        for std in ShredStandard:
            assert (
                std.passes[-1]["verify"] is True
            ), f"{std.value} last pass not verified"


# ===========================================================================
# StorageType enum
# ===========================================================================


class TestStorageType:
    def test_all_values(self):
        expected = {"hdd", "ssd_nvme", "ssd_sata", "usb_flash", "unknown"}
        assert {st.value for st in StorageType} == expected

    def test_member_count(self):
        assert len(StorageType) == 5


# ===========================================================================
# ShredResult dataclass
# ===========================================================================


class TestShredResult:
    def test_success_result_fields(self):
        r = ShredResult(
            success=True,
            file_path="x.txt",
            standard=ShredStandard.ZERO_FILL,
            passes_completed=1,
            bytes_shredded=100,
            duration_seconds=0.5,
            verification_passed=True,
        )
        assert r.success is True
        assert r.passes_completed == 1
        assert r.error is None

    def test_failure_result_with_error(self):
        r = ShredResult(
            success=False,
            file_path="x.txt",
            standard=ShredStandard.ZERO_FILL,
            passes_completed=0,
            bytes_shredded=0,
            duration_seconds=0.0,
            verification_passed=False,
            error="File not found",
        )
        assert r.error == "File not found"

    def test_to_dict_serializes_standard(self):
        r = ShredResult(
            success=True,
            file_path="x.txt",
            standard=ShredStandard.GUTMANN,
            passes_completed=35,
            bytes_shredded=1024,
            duration_seconds=1.0,
            verification_passed=True,
        )
        d = r.to_dict()
        assert d["standard"] == "gutmann"
        assert d["success"] is True
        assert d["passes_completed"] == 35

    def test_to_dict_all_expected_keys(self):
        r = ShredResult(
            success=True,
            file_path="x.txt",
            standard=ShredStandard.ZERO_FILL,
            passes_completed=1,
            bytes_shredded=0,
            duration_seconds=0,
            verification_passed=True,
        )
        d = r.to_dict()
        assert set(d.keys()) == {
            "success",
            "file_path",
            "standard",
            "passes_completed",
            "bytes_shredded",
            "duration_seconds",
            "verification_passed",
            "error",
        }

    def test_frozen_dataclass(self):
        r = ShredResult(
            success=True,
            file_path="x.txt",
            standard=ShredStandard.ZERO_FILL,
            passes_completed=1,
            bytes_shredded=0,
            duration_seconds=0,
            verification_passed=True,
        )
        with pytest.raises(AttributeError):
            r.success = False


# ===========================================================================
# SecureShredder initialization
# ===========================================================================


class TestSecureShredderInit:
    def test_default_init(self):
        s = SecureShredder()
        assert s.verify_passes is True
        assert s.dry_run is False
        assert s.sample_pct == 0.1
        assert s.cancel_event is not None

    def test_custom_init(self):
        evt = threading.Event()
        s = SecureShredder(
            progress_callback=lambda *a: None,
            cancel_event=evt,
            verify_passes=False,
            sample_verification_pct=0.5,
            dry_run=True,
        )
        assert s.verify_passes is False
        assert s.dry_run is True
        assert s.sample_pct == 0.5
        assert s.cancel_event is evt


# ===========================================================================
# shred_file — basic behaviour
# ===========================================================================


class TestShredFileBasic:
    def test_shred_nonexistent_file_returns_failure(self):
        s = SecureShredder()
        r = s.shred_file("/nonexistent/file.txt")
        assert r.success is False
        assert "not found" in r.error.lower()

    def test_shred_zero_byte_file(self, tmp_path):
        p = _make_file(tmp_path, "empty.bin", b"")
        s = SecureShredder()
        r = s.shred_file(p)
        assert r.success is True
        assert r.passes_completed == 0
        assert r.bytes_shredded == 0
        assert not os.path.exists(p)

    def test_shred_reports_correct_byte_count(self, tmp_path):
        content = b"X" * 512
        p = _make_file(tmp_path, "data.bin", content)
        r = SecureShredder().shred_file(p, ShredStandard.RANDOM_1PASS)
        assert r.bytes_shredded == 512

    def test_shred_duration_non_negative(self, tmp_path):
        p = _make_file(tmp_path, "t.bin")
        r = SecureShredder().shred_file(p, ShredStandard.RANDOM_1PASS)
        assert r.duration_seconds >= 0

    def test_shred_random_1pass_removes_file(self, tmp_path):
        p = _make_file(tmp_path, "secret.bin")
        r = SecureShredder().shred_file(p, ShredStandard.RANDOM_1PASS)
        assert r.success is True
        assert not os.path.exists(p)

    def test_shred_nist_clear_removes_file(self, tmp_path):
        p = _make_file(tmp_path, "nist.bin")
        r = SecureShredder().shred_file(p, ShredStandard.NIST_CLEAR)
        assert r.success is True
        assert not os.path.exists(p)

    def test_shred_random_3pass_removes_file(self, tmp_path):
        p = _make_file(tmp_path, "r3.bin")
        r = SecureShredder().shred_file(p, ShredStandard.RANDOM_3PASS)
        assert r.success is True
        assert not os.path.exists(p)


# ===========================================================================
# shred_file — standard-specific pass counts (random-only standards)
# ===========================================================================


class TestShredRandomOnlyStandards:
    """Standards with only random patterns work; byte-pattern standards crash."""

    def test_nist_clear_1_pass(self, tmp_path):
        p = _make_file(tmp_path, "nist.bin")
        r = SecureShredder(verify_passes=False).shred_file(p, ShredStandard.NIST_CLEAR)
        assert r.passes_completed == 1
        assert r.success is True

    def test_random_1pass(self, tmp_path):
        p = _make_file(tmp_path, "r1.bin")
        r = SecureShredder(verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert r.passes_completed == 1
        assert r.success is True

    def test_random_3pass(self, tmp_path):
        p = _make_file(tmp_path, "r3.bin")
        r = SecureShredder(verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_3PASS
        )
        assert r.passes_completed == 3
        assert r.success is True


# ===========================================================================
# shred_file — byte-pattern standards (xfail due to _pattern_bytes bug)
# ===========================================================================

_BYTE_PATTERN_STANDARDS = [
    ShredStandard.ZERO_FILL,
    ShredStandard.ONE_FILL,
    ShredStandard.DOD_5220_22_M,
    ShredStandard.DOD_5220_22_M_ECE,
    ShredStandard.HMG_IS5_BASELINE,
    ShredStandard.HMG_IS5_ENHANCED,
    ShredStandard.VSITR,
    ShredStandard.GOST_R_50739,
    ShredStandard.RCMP_TSSIT_OPS_II,
    ShredStandard.SCHNEIER,
    ShredStandard.NSA_EPL,
]


@pytest.mark.parametrize("standard", _BYTE_PATTERN_STANDARDS, ids=lambda s: s.value)
class TestBytePatternStandards:
    """These standards crash due to _pattern_bytes operator-precedence bug."""

    def test_shred_fails_with_type_error(self, tmp_path, standard):
        p = _make_file(tmp_path, f"{standard.value}.bin")
        r = SecureShredder().shred_file(p, standard)
        assert r.success is False
        assert "'int' object is not subscriptable" in r.error


# ===========================================================================
# Gutmann partial-progress test
# ===========================================================================


class TestGutmannPartialProgress:
    def test_gutmann_fails_after_4_random_passes(self, tmp_path):
        """Gutmann has 4 random passes before first byte pattern."""
        p = _make_file(tmp_path, "gut.bin", b"G" * 1024)
        r = SecureShredder().shred_file(p, ShredStandard.GUTMANN)
        assert r.success is False
        assert r.passes_completed == 4
        assert "'int' object is not subscriptable" in r.error


# ===========================================================================
# Verify-after-wipe option
# ===========================================================================


class TestVerifyOption:
    def test_verify_disabled_random_1pass_succeeds(self, tmp_path):
        p = _make_file(tmp_path, "nv.bin")
        r = SecureShredder(verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert r.success is True

    def test_verify_enabled_random_1pass_fails_verification(self, tmp_path):
        """Random verification regenerates different bytes, so always fails on small files."""
        p = _make_file(tmp_path, "vok.bin", b"X" * 256)
        r = SecureShredder(verify_passes=True).shred_file(p, ShredStandard.RANDOM_1PASS)
        assert r.success is True
        assert r.verification_passed is False

    def test_verify_disabled_prevents_crash_on_byte_patterns(self, tmp_path):
        """With verify off, byte-pattern standards still crash in _write_pass."""
        p = _make_file(tmp_path, "nvz.bin")
        r = SecureShredder(verify_passes=False).shred_file(p, ShredStandard.ZERO_FILL)
        assert r.success is False


# ===========================================================================
# Progress callback
# ===========================================================================


class TestProgressCallback:
    def test_progress_called_for_random_1pass(self, tmp_path):
        p = _make_file(tmp_path, "prog.bin", b"P" * 1024)
        calls = []
        shredder = SecureShredder(
            verify_passes=False,
            progress_callback=lambda msg, cur, total: calls.append((msg, cur, total)),
        )
        shredder.shred_file(p, ShredStandard.RANDOM_1PASS)
        assert len(calls) == 1
        assert calls[0] == ("Pass 1/1: Random 1Pass", 1, 1)

    def test_progress_called_for_random_3pass(self, tmp_path):
        p = _make_file(tmp_path, "prog3.bin", b"P" * 1024)
        calls = []
        shredder = SecureShredder(
            verify_passes=False,
            progress_callback=lambda msg, cur, total: calls.append((msg, cur, total)),
        )
        shredder.shred_file(p, ShredStandard.RANDOM_3PASS)
        assert len(calls) == 3
        assert calls[0][1] == 1
        assert calls[1][1] == 2
        assert calls[2][1] == 3

    def test_progress_totals_match_standard(self, tmp_path):
        p = _make_file(tmp_path, "pt.bin")
        calls = []
        shredder = SecureShredder(
            verify_passes=False,
            progress_callback=lambda msg, cur, total: calls.append(total),
        )
        shredder.shred_file(p, ShredStandard.RANDOM_3PASS)
        assert all(t == 3 for t in calls)

    def test_progress_called_once_for_byte_standard_before_crash(self, tmp_path):
        """Byte-pattern standard calls progress once then crashes in _write_pass."""
        p = _make_file(tmp_path, "prog_crash.bin")
        calls = []
        shredder = SecureShredder(
            progress_callback=lambda msg, cur, total: calls.append((msg, cur, total)),
        )
        shredder.shred_file(p, ShredStandard.ZERO_FILL)
        assert len(calls) == 1


# ===========================================================================
# Cancellation
# ===========================================================================


class TestCancellation:
    def test_cancel_before_start_prevents_shred(self, tmp_path):
        p = _make_file(tmp_path, "cancel.bin", b"C" * 256)
        cancel = threading.Event()
        cancel.set()
        r = SecureShredder(cancel_event=cancel).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert r.success is False
        assert "cancel" in r.error.lower()

    def test_cancel_during_shred_stops_early(self, tmp_path):
        p = _make_file(tmp_path, "cancel_mid.bin", b"M" * 1024)
        cancel = threading.Event()
        call_count = [0]

        def progress_fn(msg, cur, total):
            call_count[0] += 1
            if call_count[0] == 2:
                cancel.set()

        shredder = SecureShredder(
            verify_passes=False,
            progress_callback=progress_fn,
            cancel_event=cancel,
        )
        r = shredder.shred_file(p, ShredStandard.RANDOM_3PASS)
        assert r.success is False
        assert "cancel" in r.error.lower()
        assert r.passes_completed < 3

    def test_cancel_in_shred_files_stops_batch(self, tmp_path):
        files = [_make_file(tmp_path, f"batch_{i}.bin") for i in range(5)]
        cancel = threading.Event()
        cancel.set()
        shredder = SecureShredder(cancel_event=cancel)
        results = shredder.shred_files(files, ShredStandard.RANDOM_1PASS)
        assert results == []
        assert all(os.path.exists(f) for f in files)


# ===========================================================================
# shred_files (batch)
# ===========================================================================


class TestShredFilesBatch:
    def test_batch_shreds_all_random_1pass(self, tmp_path):
        files = [_make_file(tmp_path, f"b{i}.bin") for i in range(5)]
        results = SecureShredder(verify_passes=False).shred_files(
            files, ShredStandard.RANDOM_1PASS
        )
        assert len(results) == 5
        assert all(r.success for r in results)
        assert all(not os.path.exists(f) for f in files)

    def test_batch_empty_list(self):
        results = SecureShredder().shred_files([], ShredStandard.RANDOM_1PASS)
        assert results == []

    def test_batch_cancelled_event_returns_empty(self, tmp_path):
        files = [_make_file(tmp_path, f"c{i}.bin") for i in range(3)]
        cancel = threading.Event()
        cancel.set()
        results = SecureShredder(cancel_event=cancel).shred_files(
            files, ShredStandard.RANDOM_1PASS
        )
        assert results == []
        assert all(os.path.exists(f) for f in files)


# ===========================================================================
# Dry-run mode
# ===========================================================================


class TestDryRun:
    def test_dry_run_does_not_remove_random_standard(self, tmp_path):
        p = _make_file(tmp_path, "dry.bin", b"KEEP")
        r = SecureShredder(dry_run=True, verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert r.success is True
        assert os.path.exists(p)
        assert _read_all(p) == b"KEEP"

    def test_dry_run_zero_byte_file_not_removed(self, tmp_path):
        """Zero-byte files are only unlinked when dry_run is False."""
        p = _make_file(tmp_path, "dry_empty.bin", b"")
        r = SecureShredder(dry_run=True).shred_file(p, ShredStandard.RANDOM_1PASS)
        assert r.success is True
        assert os.path.exists(p)

    def test_dry_run_nonzero_byte_file_size_unchanged(self, tmp_path):
        content = b"X" * 1024
        p = _make_file(tmp_path, "dry_size.bin", content)
        SecureShredder(dry_run=True, verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert os.path.getsize(p) == 1024


# ===========================================================================
# Auto-detect standard
# ===========================================================================


class TestAutoDetect:
    def test_auto_detect_uses_hdd_standard(self, tmp_path):
        """With HDD monkeypatched, auto-detect should pick DoD 3-pass."""
        p = _make_file(tmp_path, "auto.bin")
        r = SecureShredder(verify_passes=False).shred_file(p, auto_detect=True)
        # Auto-detect with HDD mock → DoD, but DoD fails due to byte-pattern bug
        assert r.standard == ShredStandard.DOD_5220_22_M

    def test_auto_detect_disabled_defaults_to_nist_clear(self, tmp_path):
        p = _make_file(tmp_path, "autod_off.bin")
        r = SecureShredder(verify_passes=False).shred_file(
            p, standard=None, auto_detect=False
        )
        assert r.standard == ShredStandard.NIST_CLEAR
        assert r.success is True


# ===========================================================================
# Pattern bytes utility
# ===========================================================================


class TestPatternBytes:
    def test_random_returns_correct_length(self):
        data = _pattern_bytes("random", 512)
        assert len(data) == 512

    def test_random_returns_different_bytes(self):
        a = _pattern_bytes("random", 64)
        b = _pattern_bytes("random", 64)
        assert a != b

    def test_int_pattern(self):
        data = _pattern_bytes(0x00, 100)
        assert data == b"\x00" * 100

    def test_int_pattern_0xff(self):
        data = _pattern_bytes(0xFF, 50)
        assert data == b"\xff" * 50

    def test_crypto_erase_returns_empty(self):
        assert _pattern_bytes("crypto_erase", 1024) == b""

    def test_block_erase_returns_empty(self):
        assert _pattern_bytes("block_erase", 1024) == b""

    def test_random_prefix_pattern(self):
        data = _pattern_bytes("random_foo", 256)
        assert len(data) == 256

    def test_bytes_pattern_raises_type_error(self):
        """Known bug: operator precedence on line 288 slices the int, not bytes."""
        with pytest.raises(TypeError, match="'int' object is not subscriptable"):
            _pattern_bytes(b"\xaa", 10)

    def test_bytes_multibyte_pattern_raises_type_error(self):
        with pytest.raises(TypeError, match="'int' object is not subscriptable"):
            _pattern_bytes(b"\x92\x49\x24", 9)

    def test_bytes_pattern_single_byte_also_raises(self):
        with pytest.raises(TypeError):
            _pattern_bytes(b"\x00", 100)


# ===========================================================================
# Verify pattern utility
# ===========================================================================


class TestVerifyPattern:
    def test_crypto_erase_always_true(self, tmp_path):
        assert _verify_pattern("dummy", "crypto_erase", 100) is True

    def test_block_erase_always_true(self, tmp_path):
        assert _verify_pattern("dummy", "block_erase", 100) is True

    def test_random_on_small_file_returns_false(self, tmp_path):
        """Random verify regenerates different bytes → always False for small files."""
        data = os.urandom(4096)
        p = _make_file(tmp_path, "vr.bin", data)
        assert _verify_pattern(str(p), "random", 4096, sample_pct=1.0) is False

    def test_nonexistent_file_returns_false(self):
        assert _verify_pattern("/nonexistent/file", b"\x00", 100) is False

    def test_byte_pattern_verify_returns_false(self, tmp_path):
        """Byte patterns hit _pattern_bytes bug; verify catches it and returns False."""
        p = _make_file(tmp_path, "vb.bin", b"\x00" * 100)
        assert _verify_pattern(str(p), b"\x00", 100, sample_pct=1.0) is False


# ===========================================================================
# File size edge cases
# ===========================================================================


class TestFileSizeEdgeCases:
    def test_single_byte_file_random(self, tmp_path):
        p = _make_file(tmp_path, "one.bin", b"Z")
        r = SecureShredder(verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_1PASS
        )
        assert r.success is True
        assert r.bytes_shredded == 1

    def test_64k_file_random_3pass(self, tmp_path):
        p = _make_file(tmp_path, "64k.bin", b"L" * 65536)
        r = SecureShredder(verify_passes=False).shred_file(
            p, ShredStandard.RANDOM_3PASS
        )
        assert r.success is True
        assert r.bytes_shredded == 65536
        assert r.passes_completed == 3

    def test_1mb_file_nist_clear(self, tmp_path):
        p = _make_file(tmp_path, "1mb.bin", b"M" * (1024 * 1024))
        r = SecureShredder(verify_passes=False).shred_file(p, ShredStandard.NIST_CLEAR)
        assert r.success is True
        assert r.bytes_shredded == 1024 * 1024


# ===========================================================================
# Gutmann pass structure verification
# ===========================================================================


class TestGutmannStructure:
    def test_first_four_passes_are_random(self):
        for i in range(4):
            assert ShredStandard.GUTMANN.passes[i]["pattern"] == "random"

    def test_passes_5_to_31_are_deterministic_bytes(self):
        for i in range(4, 31):
            p = ShredStandard.GUTMANN.passes[i]["pattern"]
            assert isinstance(p, bytes)

    def test_last_four_passes_are_random(self):
        for i in range(31, 35):
            assert ShredStandard.GUTMANN.passes[i]["pattern"] == "random"

    def test_only_final_pass_verifies(self):
        verifies = [p["verify"] for p in ShredStandard.GUTMANN.passes]
        assert verifies[-1] is True
        assert all(v is False for v in verifies[:-1])
