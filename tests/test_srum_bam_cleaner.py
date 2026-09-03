"""Unit and integration tests for Windows BAM/DAM and SRUM forensic cleaner."""

import struct
from pathlib import Path
import pytest

from cortex_unified.system_tools.srum_bam_cleaner import (
    BamExecutionEntry,
    SrumBamCleaner,
    SrumBamReport,
    SrumDatabaseInfo,
)


def test_filetime_conversion():
    # Test valid FILETIME: 2026-01-01 00:00:00 UTC
    # 134116992000000000 in 100ns intervals since 1601
    ft_bytes = struct.pack("<Q", 134116992000000000)
    ts, epoch = SrumBamCleaner._filetime_to_datetime(ft_bytes)
    assert "2026-01-01" in ts
    assert epoch > 1700000000

    # Test empty or invalid bytes
    ts_empty, epoch_empty = SrumBamCleaner._filetime_to_datetime(b"")
    assert ts_empty == "Unknown"
    assert epoch_empty == 0.0

    ts_zero, epoch_zero = SrumBamCleaner._filetime_to_datetime(b"\x00" * 8)
    assert ts_zero == "Never"
    assert epoch_zero == 0.0


def test_srum_query():
    cleaner = SrumBamCleaner()
    info = cleaner.query_srum()
    assert isinstance(info, SrumDatabaseInfo)
    assert info.db_path.endswith("SRUDB.dat")


def test_srum_bam_scan():
    cleaner = SrumBamCleaner()
    report = cleaner.scan()
    assert isinstance(report, SrumBamReport)
    d = report.to_dict()
    assert "bam_entries_count" in d
    assert "srum_info" in d


def test_clean_bam_empty():
    cleaner = SrumBamCleaner()
    # Cleaning empty list should safely return 0 without error
    cleaned = cleaner.clean_bam_entries([])
    assert cleaned == 0
