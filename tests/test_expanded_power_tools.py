"""Tests for Expanded Enterprise Power Tools & System Modules.

Tests:
1. LinksManager (NTFS Junctions, Symlinks, Hardlinks)
2. FastCopier (High-Throughput File Transfer & Validation)
3. TimestampTouchEngine (MACB Timestamp & Attribute Modifier)
4. ArchiveManager (ZIP, TAR, GZ Multi-Format Studio)
5. PrefetchAnalyzer (Windows Prefetch & SysMain Trace Analyzer)
6. SearchIndexOptimizer (Windows Search Index Database Optimizer)
7. DnsBenchmarkEngine (DNS Latency Benchmark & Resolver Selector)
8. DiskBenchmarkEngine (Storage Throughput & IOPS Benchmark)
9. MemoryOptimizer (RAM & Working Set Optimizer)
10. DevCleaner (Developer Ecosystem Build Artifacts Purger)
11. BrowserDeepCleaner (Multi-Browser Deep Privacy & Cache Sanitizer)
"""

from __future__ import annotations

import datetime
import os
import platform
import tempfile
import time
from pathlib import Path

import pytest

from NexusExplorer.native.nexus_links_manager import LinksManager, LinkType
from NexusExplorer.native.nexus_fast_copier import FastCopier, CopyMode
from NexusExplorer.native.nexus_timestamp_touch import TimestampTouchEngine
from NexusExplorer.native.nexus_archive_manager import ArchiveManager, ArchiveFormat, CompressionLevel
from cortex_unified.system_tools.prefetch_analyzer import PrefetchAnalyzer
from cortex_unified.system_tools.search_index_optimizer import SearchIndexOptimizer
from cortex_unified.system_tools.dns_benchmark import DnsBenchmarkEngine, KNOWN_DNS_PROVIDERS
from cortex_unified.system_tools.disk_benchmark import DiskBenchmarkEngine
from cortex_unified.system_tools.memory_optimizer import MemoryOptimizer
from cortex_unified.system_tools.dev_cleaner import DevCleaner, DevCacheItem
from cortex_unified.system_tools.browser_deep_cleaner import BrowserDeepCleaner, BrowserTarget


def test_links_manager(tmp_path):
    """Test NTFS Links & Junctions manager capabilities."""
    target_dir = tmp_path / "target_dir"
    target_dir.mkdir()
    (target_dir / "sample.txt").write_text("hello target")

    target_file = tmp_path / "target_file.txt"
    target_file.write_text("regular file data")

    # Inspect regular item
    info = LinksManager.get_link_info(target_file)
    assert info.link_type in (LinkType.REGULAR, LinkType.HARDLINK)
    assert not info.is_broken

    # Test hardlink creation
    hardlink_path = tmp_path / "hardlink_sample.txt"
    res_hl = LinksManager.create_hardlink(hardlink_path, target_file)
    if res_hl.success:
        assert hardlink_path.exists()
        info_hl = LinksManager.get_link_info(hardlink_path)
        assert info_hl.hardlink_count >= 2
        # Remove hardlink safely
        res_rm = LinksManager.remove_link_safely(hardlink_path)
        assert res_rm.success
        assert not hardlink_path.exists()
        assert target_file.exists()

    # Scan directory
    scanned = LinksManager.scan_links_in_directory(tmp_path, recursive=False)
    assert isinstance(scanned, list)


def test_fast_copier(tmp_path):
    """Test fast asynchronous chunked copier with SHA-256 validation."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    dst_dir = tmp_path / "dst"

    # Create test payload
    f1 = src_dir / "doc1.bin"
    f1.write_bytes(b"A" * (256 * 1024))  # 256KB
    f2 = src_dir / "doc2.txt"
    f2.write_text("Hello FastCopier")

    # Run copy with SHA-256 verification
    summary = FastCopier.copy_batch(
        sources=[src_dir],
        destination_dir=dst_dir,
        mode=CopyMode.VERIFY_SHA256,
        chunk_size=64 * 1024,
    )

    assert summary.success
    assert summary.files_copied == 2
    assert summary.verified_files == 2
    assert summary.bytes_transferred > 0

    copied_f1 = dst_dir / "src" / "doc1.bin"
    assert copied_f1.exists()
    assert copied_f1.read_bytes() == f1.read_bytes()


def test_timestamp_touch(tmp_path):
    """Test forensic MACB timestamp stomper and file attributes."""
    f = tmp_path / "timestamp_test.txt"
    f.write_text("forensic payload")

    meta_before = TimestampTouchEngine.get_file_metadata(f)
    assert meta_before is not None

    # Update modified and accessed timestamps
    target_dt = datetime.datetime(2022, 5, 15, 12, 30, 0)
    res = TimestampTouchEngine.set_timestamps(
        f,
        created_time=target_dt,
        modified_time=target_dt,
        accessed_time=target_dt,
    )
    assert res.success

    meta_after = TimestampTouchEngine.get_file_metadata(f)
    assert meta_after is not None
    # Allow 2 second tolerance for filesystem timestamp precision
    assert abs(meta_after.modified_time - target_dt.timestamp()) <= 2.0


def test_archive_manager(tmp_path):
    """Test archive creation, entry listing, testing, and extraction across ZIP and TAR.GZ."""
    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    (payload_dir / "alpha.txt").write_text("Alpha content 12345")
    (payload_dir / "beta.json").write_text('{"key": "value"}')

    # 1. Create ZIP Archive
    zip_out = tmp_path / "test.zip"
    res_zip = ArchiveManager.create_archive(
        sources=[payload_dir],
        output_file=zip_out,
        fmt=ArchiveFormat.ZIP,
        compression_level=CompressionLevel.FAST,
    )
    assert res_zip.success
    assert zip_out.exists()
    assert res_zip.total_files == 2

    # 2. List entries without extraction
    entries = ArchiveManager.list_entries(zip_out)
    assert len(entries) >= 2
    filenames = [e.filename for e in entries]
    assert any("alpha.txt" in fn for fn in filenames)

    # 3. Test integrity
    ok, msg = ArchiveManager.test_archive(zip_out)
    assert ok

    # 4. Extract archive
    extract_dir = tmp_path / "extracted"
    res_ext = ArchiveManager.extract_archive(zip_out, extract_dir)
    assert res_ext.success
    assert (extract_dir / "payload" / "alpha.txt").exists()
    assert (extract_dir / "payload" / "alpha.txt").read_text() == "Alpha content 12345"

    # 5. Create TAR.GZ Archive
    tar_out = tmp_path / "test.tar.gz"
    res_tar = ArchiveManager.create_archive(
        sources=[payload_dir],
        output_file=tar_out,
        fmt=ArchiveFormat.TAR_GZ,
    )
    assert res_tar.success
    assert tar_out.exists()


def test_prefetch_analyzer():
    """Test Prefetch & SysMain analyzer metrics."""
    st = PrefetchAnalyzer.get_status()
    assert isinstance(st.total_files, int)
    assert isinstance(st.total_size_bytes, int)
    assert isinstance(st.sysmain_status, str)

    entries = PrefetchAnalyzer.scan_prefetch_files()
    assert isinstance(entries, list)


def test_search_index_optimizer():
    """Test Windows Search Index optimizer diagnostics."""
    st = SearchIndexOptimizer.get_status()
    assert isinstance(st.database_path, str)
    assert isinstance(st.database_size_bytes, int)
    assert isinstance(st.service_status, str)


def test_dns_benchmark():
    """Test DNS query builder and latency benchmarking."""
    # Test wire format builder
    q = DnsBenchmarkEngine._build_dns_query("google.com")
    assert len(q) > 12  # Header is 12 bytes
    assert b"google" in q
    assert b"com" in q

    # Benchmark Cloudflare DNS
    server = KNOWN_DNS_PROVIDERS[0]
    res = DnsBenchmarkEngine.benchmark_server(server, domains=["google.com"], timeout_seconds=1.0)
    assert isinstance(res.is_reachable, bool)
    if res.is_reachable:
        assert res.avg_ms >= 0.0


def test_disk_benchmark(tmp_path):
    """Test disk benchmark throughput and IOPS measurement on sandbox directory."""
    report = DiskBenchmarkEngine.run_benchmark(tmp_path, file_size_mb=4)
    assert report.error is None
    assert report.sequential_write.speed_mb_s >= 0.0
    assert report.sequential_read.speed_mb_s >= 0.0
    assert report.random_write_4k.iops >= 0.0
    assert report.random_read_4k.iops >= 0.0
    assert report.elapsed_seconds > 0.0


def test_memory_optimizer():
    """Test system RAM metrics and process memory inspection."""
    metrics = MemoryOptimizer.get_system_ram_metrics()
    assert metrics.total_bytes > 0
    assert metrics.used_bytes > 0
    assert 0.0 <= metrics.percent_used <= 100.0

    procs = MemoryOptimizer.scan_process_memory(limit=10)
    assert len(procs) > 0
    for p in procs:
        assert p.pid > 0
        assert p.working_set_bytes >= 0


def test_dev_cleaner():
    """Test developer ecosystem build artifact scanner."""
    caches = DevCleaner.scan_dev_caches()
    assert isinstance(caches, list)
    for c in caches:
        assert isinstance(c.ecosystem, str)
        assert isinstance(c.name, str)
        assert c.size_bytes >= 0


def test_browser_deep_cleaner():
    """Test multi-browser deep privacy and cache scanner."""
    targets = BrowserDeepCleaner.scan_browser_caches()
    assert isinstance(targets, list)
    for t in targets:
        assert isinstance(t.browser_name, str)
        assert isinstance(t.category, str)
        assert t.size_bytes >= 0
