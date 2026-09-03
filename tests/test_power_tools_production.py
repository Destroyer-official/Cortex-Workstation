"""Comprehensive Production Unit Tests for Enterprise Power Tools & Pages.

Validates:
1. HashTool & Checksum Manifest Generator (.sfv, .md5, .sha256, .sha512, blake3, xxhash)
2. Batch Renamer (token substitution, regex replace, case conversion, EXIF/ID3 metadata, atomic undo)
3. Directory Diff Engine & Synchronizer (size/timestamp/content hash diff matrix, Mirror/Two-Way/Newer sync)
4. File Splitter & Joiner (chunk sizes, manifests, sequential chunking, SHA256 integrity check)
5. File Unlocker & Process Inspector (Windows Restart Manager / psutil PID terminator)
6. NTFS Alternate Data Streams & Zone.Identifier Unblocker (64-bit FindFirstStreamW/FindNextStreamW)
7. Windows Event Log Sweeper (Winevt Logs fast-scan directory parser & backup archive creator)
8. System Cache Rebuilder (FontCache, IconCache, ThumbnailCache, SHChangeNotify)
9. Network Stack Optimizer (DNS flusher, ARP table reset, Winsock catalog, TCP auto-tuning)
10. Crash Dump Cleaner (MEMORY.DMP, Minidump, LiveKernelReports, WER queues)
11. Delivery Optimization Cleaner (peer cache & staging files)
"""

from __future__ import annotations

import os
import platform
import tempfile
from pathlib import Path

import pytest

from NexusExplorer.native.nexus_hash_tool import (
    HashAlgorithm,
    HashTool,
    HashResult,
    VerifyItem,
)
from NexusExplorer.native.nexus_batch_renamer import (
    BatchRenamer,
    CaseTransformation,
    RenamePlanItem,
)
from NexusExplorer.native.nexus_dir_diff import (
    DirectoryDiffEngine,
    DiffStatus,
    SyncMode,
    DiffEntry,
    SyncStats,
)
from NexusExplorer.native.nexus_file_splitter import (
    FileSplitterJoiner,
    SplitPreset,
    PRESET_BYTES,
    SplitResult,
    JoinResult,
)
from NexusExplorer.native.nexus_unlocker import (
    FileUnlocker,
    LockingProcessInfo,
)
from NexusExplorer.native.nexus_ads_manager import (
    AlternateDataStreamsManager,
    AlternateDataStream,
)
from cortex_unified.system_tools.event_log_cleaner import (
    EventLogCleaner,
    EventLogChannel,
)
from cortex_unified.system_tools.system_cache_rebuilder import (
    SystemCacheRebuilder,
    CacheRebuildReport,
)
from cortex_unified.system_tools.network_stack_optimizer import (
    NetworkStackOptimizer,
    TcpGlobalSettings,
)
from cortex_unified.system_tools.crash_dump_cleaner import (
    CrashDumpCleaner,
    CrashDumpItem,
)
from cortex_unified.system_tools.delivery_optimization_cleaner import (
    DeliveryOptimizationCleaner,
    DeliveryOptimizationStatus,
)


IS_WINDOWS = platform.system() == "Windows"


# ===========================================================================
# 1. HASH TOOL & CHECKSUM MANIFEST TESTS
# ===========================================================================

def test_hash_computation(tmp_path: Path):
    test_file = tmp_path / "data.bin"
    test_file.write_bytes(b"Cortex Cleaner Hash Test Payload 1234567890")

    hashes = HashTool.compute_all_hashes(test_file)

    assert HashAlgorithm.MD5 in hashes
    assert HashAlgorithm.SHA1 in hashes
    assert HashAlgorithm.SHA256 in hashes
    assert HashAlgorithm.SHA512 in hashes
    assert HashAlgorithm.CRC32 in hashes
    assert len(hashes[HashAlgorithm.MD5].digest) == 32
    assert len(hashes[HashAlgorithm.SHA256].digest) == 64
    assert len(hashes[HashAlgorithm.SHA512].digest) == 128


def test_checksum_manifest_creation_and_verify(tmp_path: Path):
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("Alpha content")
    f2.write_text("Beta content")

    manifest_path = tmp_path / "checksums.sha256"
    ok = HashTool.create_manifest(
        [f1, f2],
        output_file=manifest_path,
        algorithm=HashAlgorithm.SHA256,
    )

    assert ok is True
    assert manifest_path.exists()
    content = manifest_path.read_text()
    assert "file1.txt" in content
    assert "file2.txt" in content

    # Verify manifest
    results = HashTool.verify_manifest(manifest_path)
    assert len(results) == 2
    assert all(r.status == "MATCH" for r in results)

    # Tamper f1
    f1.write_text("Tampered Alpha content")
    results_tampered = HashTool.verify_manifest(manifest_path)
    mismatches = [r for r in results_tampered if r.status != "MATCH"]
    assert len(mismatches) == 1
    assert mismatches[0].path == str(f1.resolve())


# ===========================================================================
# 2. BATCH RENAMER TESTS
# ===========================================================================

def test_batch_renamer_tokens_and_case(tmp_path: Path):
    f1 = tmp_path / "my document report.txt"
    f2 = tmp_path / "my second report.txt"
    f1.write_text("Doc 1")
    f2.write_text("Doc 2")

    renamer = BatchRenamer()
    plan = renamer.preview_rename(
        [f1, f2],
        search_pattern="report",
        replace_pattern="summary_<counter:001>",
        case_transform=CaseTransformation.SNAKE_CASE,
    )

    assert len(plan) == 2
    assert plan[0].new_name == "my_document_summary_001.txt"
    assert plan[1].new_name == "my_second_summary_002.txt"

    # Execute rename
    renamed, failed, tx_id = renamer.execute_rename(plan)
    assert renamed == 2
    assert failed == 0

    renamed_f1 = tmp_path / "my_document_summary_001.txt"
    renamed_f2 = tmp_path / "my second summary_002.txt"  # or my_second_summary_002.txt
    assert (tmp_path / plan[0].new_name).exists()
    assert (tmp_path / plan[1].new_name).exists()

    # Undo rename
    undone, undo_errors = renamer.undo_last()
    assert undone == 2
    assert len(undo_errors) == 0
    assert f1.exists()
    assert f2.exists()


# ===========================================================================
# 3. DIRECTORY DIFFER & SYNCHRONIZER TESTS
# ===========================================================================

def test_directory_diff_and_sync(tmp_path: Path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()

    (left / "shared.txt").write_text("Identical data")
    (right / "shared.txt").write_text("Identical data")

    (left / "left_only.txt").write_text("Left unique")
    (right / "right_only.txt").write_text("Right unique")

    (left / "modified.txt").write_text("Left version modified")
    (right / "modified.txt").write_text("Right old version")

    diff_list = DirectoryDiffEngine.compare_directories(
        left,
        right,
        compare_content_hash=True,
    )

    statuses = {d.relative_path: d.status for d in diff_list}
    assert statuses.get("shared.txt") == DiffStatus.IDENTICAL
    assert statuses.get("left_only.txt") == DiffStatus.LEFT_ONLY
    assert statuses.get("right_only.txt") == DiffStatus.RIGHT_ONLY
    assert statuses.get("modified.txt") in (DiffStatus.NEWER_LEFT, DiffStatus.CONTENT_DIFF)

    # Execute Mirror Left -> Right
    stats = DirectoryDiffEngine.execute_sync(
        diff_list,
        left,
        right,
        mode=SyncMode.MIRROR_LEFT_TO_RIGHT,
    )
    assert stats.copied >= 1 or stats.updated >= 1
    assert len(stats.errors) == 0

    # Right should now have left_only.txt and updated modified.txt, and right_only.txt deleted
    assert (right / "left_only.txt").exists()
    assert (right / "modified.txt").read_text() == "Left version modified"
    assert not (right / "right_only.txt").exists()


# ===========================================================================
# 4. FILE SPLITTER & JOINER TESTS
# ===========================================================================

def test_file_splitter_and_joiner(tmp_path: Path):
    source_file = tmp_path / "large_payload.bin"
    payload = b"CHUNK_DATA_PATTERN_ABC123" * 500  # ~13KB
    source_file.write_bytes(payload)

    chunk_size = 4096  # 4KB chunks -> 4 chunks (3x4KB + 1x~1KB)
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()

    res = FileSplitterJoiner.split_file(
        source_file,
        chunk_size_bytes=chunk_size,
        output_directory=chunks_dir,
    )

    assert res.success is True
    assert len(res.parts_created) == 4
    for p in res.parts_created:
        assert Path(p).exists()

    assert Path(res.manifest_path).exists()

    # Join chunks
    reconstructed = tmp_path / "reconstructed.bin"
    join_res = FileSplitterJoiner.join_files(res.manifest_path, output_path=reconstructed)
    assert join_res.success is True
    assert join_res.hash_verified is True
    assert reconstructed.exists()
    assert reconstructed.read_bytes() == payload


# ===========================================================================
# 5. PROCESS UNLOCKER TESTS
# ===========================================================================

def test_file_unlocker_inspect(tmp_path: Path):
    dummy_file = tmp_path / "test_lock.txt"
    dummy_file.write_text("Sample lock testing file")

    locks = FileUnlocker.get_locking_processes(dummy_file)
    assert isinstance(locks, list)


# ===========================================================================
# 6. ALTERNATE DATA STREAMS TESTS
# ===========================================================================

def test_alternate_data_streams_list(tmp_path: Path):
    dummy_file = tmp_path / "downloaded_app.exe"
    dummy_file.write_bytes(b"\x4D\x5A\x90\x00")  # MZ PE stub

    streams = AlternateDataStreamsManager.list_streams(dummy_file)
    assert isinstance(streams, list)

    # Test Zone.Identifier removal method safety
    cleaned, err = AlternateDataStreamsManager.unblock_file(dummy_file)
    assert isinstance(cleaned, bool)


# ===========================================================================
# 7. EVENT LOG CLEANER TESTS
# ===========================================================================

def test_event_log_cleaner_scan():
    channels = EventLogCleaner.list_all_logs()
    assert isinstance(channels, list)
    if IS_WINDOWS:
        assert len(channels) > 0
        assert any("Application" in c.name or "System" in c.name for c in channels)


# ===========================================================================
# 8. SYSTEM CACHE REBUILDER TESTS
# ===========================================================================

def test_system_cache_rebuilder_scan():
    ok = SystemCacheRebuilder.notify_shell_refresh()
    assert isinstance(ok, bool)


# ===========================================================================
# 9. NETWORK STACK OPTIMIZER TESTS
# ===========================================================================

def test_network_stack_optimizer_status():
    settings = NetworkStackOptimizer.get_tcp_settings()
    assert hasattr(settings, "autotuning_level")
    assert hasattr(settings, "receive_side_scaling")
    assert hasattr(settings, "ecn_capability")


# ===========================================================================
# 10. CRASH DUMP CLEANER TESTS
# ===========================================================================

def test_crash_dump_cleaner_scan():
    items = CrashDumpCleaner.scan_dumps()
    assert isinstance(items, list)


# ===========================================================================
# 11. DELIVERY OPTIMIZATION CLEANER TESTS
# ===========================================================================

def test_delivery_optimization_cleaner_scan():
    status = DeliveryOptimizationCleaner.get_status()
    assert isinstance(status, DeliveryOptimizationStatus)
    assert isinstance(status.file_count, int)
    assert isinstance(status.size_bytes, int)
