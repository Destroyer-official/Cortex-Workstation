"""Comprehensive test suite for Next-Generation Enterprise System Tools & Forensics.

Tests:
1. ShaderCacheCleaner
2. AiTelemetryCleaner
3. SsdTrimOptimizer
4. RestartManagerUnlocker
5. VssHealthAnalyzer
6. DevPackageCacheCleaner
7. ChecksumMatrix
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from cortex_unified.system_tools.shader_cache_cleaner import ShaderCacheCleaner
from cortex_unified.system_tools.ai_telemetry_cleaner import AiTelemetryCleaner
from cortex_unified.system_tools.ssd_trim_optimizer import SsdTrimOptimizer
from cortex_unified.system_tools.restart_manager_unlocker import RestartManagerUnlocker
from cortex_unified.system_tools.vss_health_analyzer import VssHealthAnalyzer
from cortex_unified.system_tools.dev_package_cache_cleaner import DevPackageCacheCleaner
from cortex_unified.system_tools.checksum_matrix import ChecksumMatrix


def test_shader_cache_cleaner_scan_and_clean():
    """Test ShaderCacheCleaner scan, age filtering, and dry-run cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        fake_cache = tmp / "D3DSCache"
        fake_cache.mkdir()
        (fake_cache / "shader1.bin").write_bytes(b"\x00" * 1024)
        (fake_cache / "shader2.bin").write_bytes(b"\x00" * 2048)

        cleaner = ShaderCacheCleaner()
        # Override known locations for unit testing
        cleaner.get_known_locations = lambda: [("Test DirectX Cache", "Microsoft", fake_cache)]

        report = cleaner.scan(min_age_days=0)
        assert report.total_files == 2
        assert report.total_bytes == 3072
        assert len(report.locations) == 1

        # Test dry-run
        dry_res = cleaner.clean(min_age_days=0, dry_run=True)
        assert dry_res.cleaned_files == 2
        assert dry_res.freed_bytes == 3072
        assert (fake_cache / "shader1.bin").exists()

        # Test real clean
        real_res = cleaner.clean(min_age_days=0, dry_run=False)
        assert real_res.cleaned_files == 2
        assert not (fake_cache / "shader1.bin").exists()
        assert not (fake_cache / "shader2.bin").exists()


def test_ai_telemetry_cleaner_wal_checkpoint():
    """Test AiTelemetryCleaner SQLite WAL checkpointing and truncation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        db_path = tmp / "test_store.db"

        # Create real SQLite DB in WAL mode
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, data TEXT);")
        for i in range(100):
            conn.execute("INSERT INTO records (data) VALUES (?);", (f"record_{i}",))
        conn.commit()
        conn.close()

        wal_path = tmp / "test_store.db-wal"
        cleaner = AiTelemetryCleaner()

        # Checkpoint WAL
        if wal_path.exists():
            freed = cleaner.checkpoint_wal_journal(wal_path)
            assert freed >= 0

        # Override candidate stores
        cleaner._get_search_roots = lambda: [("Test Store", "Recall", tmp, "Test Description")]
        report = cleaner.scan()
        assert len(report.artifacts) >= 1
        assert report.total_size_bytes > 0

        # Dry run clean
        c_res = cleaner.clean(checkpoint_wal=True, dry_run=True)
        assert c_res.dry_run is True


def test_ssd_trim_optimizer():
    """Test SsdTrimOptimizer volume auditing and retrim execution."""
    opt = SsdTrimOptimizer()
    ntfs_ok, refs_ok = opt.query_global_trim_enabled()
    assert isinstance(ntfs_ok, bool)
    assert isinstance(refs_ok, bool)

    report = opt.audit_volumes()
    assert isinstance(report.volumes, list)
    assert report.scan_duration_ms >= 0.0

    # Test retrim execution on system drive
    res = opt.retrim_volume("C")
    assert res.drive_letter == "C"
    assert isinstance(res.success, bool)


def test_restart_manager_unlocker():
    """Test RestartManagerUnlocker lock inspection and safe unlock."""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"content")
        f_path = f.name

    try:
        unlocker = RestartManagerUnlocker()
        rep = unlocker.inspect_locks(f_path)
        assert rep.exists is True
        assert isinstance(rep.is_locked, bool)
        assert isinstance(rep.locking_processes, list)

        # File is currently unlocked
        res = unlocker.unlock_file(f_path)
        assert res.success is True
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_vss_health_analyzer():
    """Test VssHealthAnalyzer status parsing and reset logic."""
    analyzer = VssHealthAnalyzer()
    sample_text = (
        "Writer name: 'System Writer'\n"
        "   Writer Id: {e81062d3-180e-4366-b94f-95cb2778ac9f}\n"
        "   Writer Instance Id: {12345678-1234-1234-1234-123456789012}\n"
        "   State: [1] Stable\n"
        "   Last error: No error\n\n"
        "Writer name: 'MSSearch Writer'\n"
        "   Writer Id: {cd3f0c32-b7e1-45be-a827-024c0429f528}\n"
        "   State: [5] Waiting for completion\n"
        "   Last error: Retryable error\n"
    )

    writers = analyzer._parse_writers(sample_text)
    assert len(writers) == 2
    assert writers[0].is_healthy is True
    assert writers[0].state_code == 1
    assert writers[1].is_healthy is False
    assert writers[1].state_code == 5

    rep = analyzer.inspect_health()
    assert isinstance(rep.writers, list)
    assert rep.scan_duration_ms >= 0.0


def test_dev_package_cache_cleaner():
    """Test DevPackageCacheCleaner store analysis and dry-run purging."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        fake_store = tmp / "cargo_cache"
        fake_store.mkdir()
        (fake_store / "crate1.crate").write_bytes(b"\x00" * 512)

        cleaner = DevPackageCacheCleaner()
        cleaner.get_candidate_stores = lambda: [
            ("Test Cargo Cache", "Cargo", fake_store, "Test Cargo Store")
        ]

        report = cleaner.scan()
        assert report.total_packages == 1
        assert report.total_bytes == 512

        # Dry run clean
        c_res = cleaner.clean(dry_run=True)
        assert c_res.deleted_packages == 1
        assert c_res.freed_bytes == 512
        assert (fake_store / "crate1.crate").exists()


def test_checksum_matrix_manifest_flow():
    """Test ChecksumMatrix hashing, manifest generation, and verification."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        f1 = tmp / "sample1.txt"
        f2 = tmp / "sample2.txt"
        f1.write_text("Hello World", encoding="utf-8")
        f2.write_text("Cortex Cleaner Suite", encoding="utf-8")

        matrix = ChecksumMatrix()
        hres = matrix.hash_file(f1, algorithms=["crc32", "md5", "sha256"])
        assert hres.crc32 != ""
        assert hres.md5 != ""
        assert hres.sha256 != ""
        assert hres.size_bytes == 11

        manifest = tmp / "checksums.sha256"
        count = matrix.generate_manifest(tmp, manifest, algorithm="sha256")
        assert count == 2
        assert manifest.is_file()

        # Verify manifest (all valid)
        v_rep = matrix.verify_manifest(manifest)
        assert v_rep.is_all_valid is True
        assert v_rep.matched_files == 2
        assert v_rep.mismatched_files == 0
        assert v_rep.missing_files == 0

        # Corrupt one file
        f2.write_text("Corrupted content", encoding="utf-8")
        v_rep_corrupted = matrix.verify_manifest(manifest)
        assert v_rep_corrupted.is_all_valid is False
        assert v_rep_corrupted.mismatched_files == 1
        assert v_rep_corrupted.matched_files == 1
