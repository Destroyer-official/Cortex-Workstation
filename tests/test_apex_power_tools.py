"""Unit tests for the 10 Apex Enterprise Power Tools and Forensic Modules."""

import os
import tempfile
from pathlib import Path

from NexusExplorer.native.file_signature_sniffer import FileSignatureSniffer, SniffResult
from NexusExplorer.native.binary_differ import BinaryDiffer, BinaryDiffReport
from NexusExplorer.native.usn_journal_scanner import UsnJournalScanner, UsnJournalStatus
from NexusExplorer.native.par2_recovery import Par2RecoveryEngine, Par2ValidationReport
from NexusExplorer.native.image_optimizer import ImageOptimizer, ImageOptimizeResult
from cortex_unified.system_tools.driver_store_cleaner import DriverStoreCleaner
from cortex_unified.system_tools.power_plan_optimizer import PowerPlanOptimizer, PowerPlanStatus
from cortex_unified.system_tools.shellbags_privacy_cleaner import ShellbagsPrivacyCleaner
from cortex_unified.system_tools.hosts_file_manager import HostsFileManager, HostEntry
from cortex_unified.system_tools.notification_cleaner import NotificationCleaner


def test_file_signature_sniffer(tmp_path):
    # 1. Test PNG Header
    """test_file_signature_sniffer.

    Manages test file signature sniffer operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 32)
    res = FileSignatureSniffer.sniff_file(png_file)
    assert not res.is_spoofed
    assert "Portable Network Graphics" in res.detected_format or "png" in res.detected_mime.lower()

    # 2. Test Spoofed Executable disguised as PNG
    spoofed = tmp_path / "malicious.png"
    spoofed.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 32)
    res_spoof = FileSignatureSniffer.sniff_file(spoofed)
    assert res_spoof.is_spoofed
    assert "Executable" in res_spoof.detected_format or "PE" in res_spoof.detected_format


def test_binary_differ(tmp_path):
    """test_binary_differ.

    Manages test binary differ operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    fa = tmp_path / "file_a.bin"
    fb = tmp_path / "file_b.bin"

    fa.write_bytes(b"HELLO_WORLD_TEST_DATA_PAYLOAD_1234567890")
    fb.write_bytes(b"HELLO_WORLD_TEST_DIFF_PAYLOAD_1234567890")

    rep = BinaryDiffer.compare_binary_files(fa, fb)
    assert not rep.is_identical
    assert rep.matching_percentage > 80.0
    assert rep.total_differences_bytes > 0
    assert rep.first_difference_offset == 18
    assert len(rep.diff_chunks) > 0


def test_usn_journal_scanner():
    """test_usn_journal_scanner.

    Manages test usn journal scanner operations and coordinates related state changes for the component.
    """
    st = UsnJournalScanner.query_volume_journal("C:")
    assert isinstance(st, UsnJournalStatus)
    assert st.drive_letter == "C:"
    # Either active on NTFS or returns proper permission/unsupported status
    assert st.is_supported or "Access denied" in str(st.error) or "Windows NTFS only" in str(st.error)


def test_par2_recovery(tmp_path):
    """test_par2_recovery.

    Manages test par2 recovery operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    par2_file = tmp_path / "test.par2"
    # Write a mock PAR2 packet header: Magic (8B) + Length (8B) + Hash (16B) + SetID (16B) + Type (16B) + Body
    magic = b"PAR2\x00PKT"
    body = b"\x00" * 32
    pkt_len = 64 + len(body)
    packet_hdr = magic + pkt_len.to_bytes(8, "little") + b"\x00" * 16 + b"\x11" * 16 + b"PAR 2.0\x00Main\x00\x00\x00\x00"
    par2_file.write_bytes(packet_hdr + body)

    rep = Par2RecoveryEngine.inspect_par2_file(par2_file)
    assert isinstance(rep, Par2ValidationReport)
    assert rep.is_valid_par2
    assert len(rep.packets) >= 1


def test_image_optimizer(tmp_path):
    """test_image_optimizer.

    Manages test image optimizer operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    from PySide6.QtGui import QImage, QColor

    img_path = tmp_path / "test.png"
    img = QImage(64, 64, QImage.Format.Format_RGB32)
    img.fill(QColor(255, 0, 0))
    img.save(str(img_path))

    out_path = tmp_path / "test_opt.webp"
    res = ImageOptimizer.optimize_image(img_path, output_path=out_path, target_format="webp", quality=80)
    assert res.success
    assert Path(res.output_path).exists()
    assert res.compressed_size_bytes > 0


def test_driver_store_cleaner():
    """test_driver_store_cleaner.

    Manages test driver store cleaner operations and coordinates related state changes for the component.
    """
    drivers = DriverStoreCleaner.enumerate_drivers()
    assert isinstance(drivers, list)
    # On Windows test system, verifies driver parse format or empty graceful handling
    if drivers:
        d = drivers[0]
        assert bool(d.published_name)


def test_power_plan_optimizer():
    """test_power_plan_optimizer.

    Manages test power plan optimizer operations and coordinates related state changes for the component.
    """
    st = PowerPlanOptimizer.get_status()
    assert isinstance(st, PowerPlanStatus)
    assert bool(st.active_scheme_name)


def test_shellbags_privacy_cleaner():
    """test_shellbags_privacy_cleaner.

    Manages test shellbags privacy cleaner operations and coordinates related state changes for the component.
    """
    targets = ShellbagsPrivacyCleaner.scan_shell_activity()
    assert isinstance(targets, list)
    # Test dry calculation
    for t in targets:
        assert bool(t.category)
        assert t.items_count >= 0


def test_hosts_file_manager(tmp_path):
    """test_hosts_file_manager.

    Manages test hosts file manager operations and coordinates related state changes for the component.

    Args:
        tmp_path: Filesystem path to the target file or directory.
    """
    mock_hosts = tmp_path / "mock_hosts"
    mock_hosts.write_text(
        "127.0.0.1 localhost\n"
        "# 192.168.1.50 testserver\n"
        "0.0.0.0 telemetry.microsoft.com # Anti-Telemetry\n",
        encoding="utf-8",
    )

    entries = HostsFileManager.parse_hosts_file(mock_hosts)
    assert len(entries) == 3
    assert entries[0].hostname == "localhost"
    assert entries[0].is_enabled
    assert entries[1].hostname == "testserver"
    assert not entries[1].is_enabled
    assert entries[2].hostname == "telemetry.microsoft.com"

    # Test applying shield
    res = HostsFileManager.apply_anti_telemetry_shield(mock_hosts)
    assert res.success
    updated = HostsFileManager.parse_hosts_file(mock_hosts)
    assert len(updated) > len(entries)


def test_notification_cleaner():
    """test_notification_cleaner.

    Manages test notification cleaner operations and coordinates related state changes for the component.
    """
    st = NotificationCleaner.get_status()
    assert hasattr(st, "total_size_bytes")
    assert st.total_size_bytes >= 0
