"""Tests for Enterprise Next-Gen Storage, Security & Forensics Suite tools."""

import os
import tempfile
import time
from pathlib import Path

import pytest

from cortex_unified.system_tools.vss_manager import VssManager, VssAuditReport
from cortex_unified.system_tools.dev_drive_optimizer import DevDriveOptimizer, DevDriveAuditReport
from cortex_unified.system_tools.bitlocker_auditor import BitLockerAuditor, BitLockerAuditReport
from cortex_unified.system_tools.junction_auditor import JunctionAuditor, JunctionAuditReport
from cortex_unified.system_tools.bitrot_scrubber import BitRotScrubber, BitRotScrubReport
from cortex_unified.system_tools.memory_compression_tuner import MemoryCompressionTuner, MemoryTunerReport
from cortex_unified.system_tools.sandbox_cleaner import SandboxCleaner, SandboxCleanReport
from cortex_unified.system_tools.smb_share_auditor import SmbShareAuditor, SmbSecurityReport
from cortex_unified.system_tools.process_token_auditor import ProcessTokenAuditor, ProcessTokenAuditReport
from cortex_unified.system_tools.storage_growth_tracker import StorageGrowthTracker, SnapshotSummary, StorageGrowthDiffReport


def test_vss_manager():
    """test_vss_manager."""
    mgr = VssManager()
    rep = mgr.audit()
    assert isinstance(rep, VssAuditReport)
    assert rep.total_used_bytes >= 0
    assert rep.total_allocated_bytes >= 0
    assert isinstance(rep.shadows, list)
    assert isinstance(rep.storages, list)


def test_dev_drive_optimizer():
    """test_dev_drive_optimizer."""
    opt = DevDriveOptimizer()
    rep = opt.audit()
    assert isinstance(rep, DevDriveAuditReport)
    assert isinstance(rep.drives, list)
    assert len(rep.drives) > 0  # Should find at least C: on Windows
    c_drive = rep.drives[0]
    assert c_drive.drive_letter.endswith(":")
    assert c_drive.total_space_bytes > 0


def test_bitlocker_auditor():
    """test_bitlocker_auditor."""
    aud = BitLockerAuditor()
    rep = aud.audit()
    assert isinstance(rep, BitLockerAuditReport)
    assert rep.fully_protected_count >= 0
    assert rep.unprotected_count >= 0
    assert isinstance(rep.warnings, list)


def test_junction_auditor():
    """test_junction_auditor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        sub = tmp / "real_folder"
        sub.mkdir()
        (sub / "sample.txt").write_text("hello", encoding="utf-8")

        # Create symlink if privileges allow, or test directory scan
        aud = JunctionAuditor()
        rep = aud.audit(str(tmp))
        assert isinstance(rep, JunctionAuditReport)
        assert rep.total_reparse_points >= 0


def test_bitrot_scrubber(tmp_path):
    """test_bitrot_scrubber."""
    db_file = tmp_path / "scrub_db" / "test_scrub.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    scan_dir = tmp_path / "scan_data"
    scan_dir.mkdir(parents=True, exist_ok=True)

    f1 = scan_dir / "file1.txt"
    f1.write_text("original data content 123456", encoding="utf-8")

    scrubber = BitRotScrubber(str(db_file))

    # First scrub pass: index baseline
    rep1 = scrubber.scrub(str(scan_dir))
    assert rep1.total_files_scanned >= 1
    assert rep1.new_files_indexed >= 1
    assert rep1.corrupted_count == 0

    # Second scrub pass: verified clean
    rep2 = scrubber.scrub(str(scan_dir))
    assert rep2.clean_files_count >= 1
    assert rep2.corrupted_count == 0

    # Simulate silent bitrot: mutate content while keeping mtime and size identical!
    st = f1.stat()
    orig_mtime = st.st_mtime
    f1.write_text("mutated! data content 123456", encoding="utf-8")
    os.utime(f1, (orig_mtime, orig_mtime))

    rep3 = scrubber.scrub(str(scan_dir))
    assert rep3.corrupted_count == 1
    assert rep3.corrupted_items[0].path == str(f1.resolve())


def test_memory_compression_tuner():
    """test_memory_compression_tuner."""
    tuner = MemoryCompressionTuner()
    rep = tuner.audit()
    assert isinstance(rep, MemoryTunerReport)
    if rep.status:
        assert rep.status.total_physical_ram_bytes > 0
        assert rep.status.available_physical_ram_bytes > 0
        assert rep.status.compression_ratio >= 1.0


def test_sandbox_cleaner():
    """test_sandbox_cleaner."""
    cleaner = SandboxCleaner()
    rep = cleaner.scan()
    assert isinstance(rep, SandboxCleanReport)
    assert rep.total_reclaimable_bytes >= 0
    assert isinstance(rep.artifacts, list)


def test_smb_share_auditor():
    """test_smb_share_auditor."""
    aud = SmbShareAuditor()
    rep = aud.audit()
    assert isinstance(rep, SmbSecurityReport)
    assert rep.total_shares >= 0
    assert isinstance(rep.shares, list)


def test_process_token_auditor():
    """test_process_token_auditor."""
    aud = ProcessTokenAuditor()
    rep = aud.audit(max_processes=20)
    assert isinstance(rep, ProcessTokenAuditReport)
    assert len(rep.processes) > 0
    first_p = rep.processes[0]
    assert first_p.pid >= 0
    assert first_p.integrity_level in ["Untrusted", "Low", "Medium", "High", "System", "Unknown"]


def test_storage_growth_tracker(tmp_path):
    """test_storage_growth_tracker."""
    db_file = tmp_path / "tracker_db" / "growth.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    scan_dir = tmp_path / "tracked_dir"
    scan_dir.mkdir(parents=True, exist_ok=True)

    tracker = StorageGrowthTracker(str(db_file))

    # Snapshot 1: initial empty folder
    f1 = scan_dir / "initial.dat"
    f1.write_bytes(b"A" * 1024)
    s1 = tracker.take_snapshot(str(scan_dir), label="Baseline")
    assert s1.total_bytes == 1024
    assert s1.total_files == 1

    # Snapshot 2: add more files
    f2 = scan_dir / "growth.dat"
    f2.write_bytes(b"B" * 4096)
    s2 = tracker.take_snapshot(str(scan_dir), label="After Growth")
    assert s2.total_bytes == 5120
    assert s2.total_files == 2

    # Compare snapshots
    diff = tracker.compare_snapshots(s1.snapshot_id, s2.snapshot_id)
    assert isinstance(diff, StorageGrowthDiffReport)
    assert diff.net_growth_bytes == 4096
    assert len(diff.top_growing_dirs) >= 1
