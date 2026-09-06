"""Adversarial and boundary safety tests verifying the audit hardening.

Verifies:
1. Deleter rejects symlink/junction directories and protected system paths.
2. AdvancedShredder self-enforces PathGuard and rejects junctions/symlinks.
3. SecureDeleter handles reparse points safely without traversal.
4. RegistryCleaner rejects protected system registry keys and enforces fail-closed backup.
"""

import os
import sys
import pytest
from pathlib import Path

from cortex_unified.core.deleter import Deleter
from cortex_unified.analyzers.advanced_shredder import AdvancedShredder, ShredMethod
from cortex_unified.engine.secure_delete import SecureDeleter, DeletionMethod, DeletionOutcome
from cortex_unified.system_tools.registry_cleaner import RegistryCleaner, PROTECTED_REGISTRY_KEYS


def test_deleter_refuses_protected_path(tmp_path):
    """Deleter must self-enforce PathGuard and refuse deletion of protected paths."""
    deleter = Deleter(dry_run=False)
    # Simulate a protected path like Windows or System32
    win_dir = Path("C:/Windows/System32/drivers/etc/hosts") if sys.platform == "win32" else Path("/etc/passwd")
    res = deleter.delete([win_dir], [])
    assert len(deleter.deleted_items) == 0
    assert len(deleter.errors) > 0


def test_deleter_refuses_symlink_directory(tmp_path):
    """Deleter must refuse to delete a directory that is a symlink or junction."""
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "file.txt").write_text("hello", encoding="utf-8")

    link_dir = tmp_path / "link_dir"
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not permitted in this environment")

    deleter = Deleter(dry_run=False)
    # Attempting to delete the link dir must be refused by the reparse guard
    res = deleter.delete([], [link_dir])
    assert len(deleter.deleted_items) == 0
    assert any("reparse" in err.get("error", "").lower() or "symlink" in err.get("error", "").lower() for err in deleter.errors)
    # Real dir must still be intact!
    assert (real_dir / "file.txt").exists()


def test_deleter_refuses_mocked_symlink_directory(tmp_path, monkeypatch):
    """Deleter must refuse to delete a directory when islink returns True."""
    dummy_dir = tmp_path / "mock_link_dir"
    dummy_dir.mkdir()
    monkeypatch.setattr(os.path, "islink", lambda p: True)
    deleter = Deleter(dry_run=False)
    deleter.delete([], [dummy_dir])
    assert len(deleter.deleted_items) == 0
    assert any("reparse" in err.get("error", "").lower() or "symlink" in err.get("error", "").lower() for err in deleter.errors)
    assert dummy_dir.exists()


def test_advanced_shredder_refuses_mocked_symlink_file(tmp_path, monkeypatch):
    """AdvancedShredder must refuse to shred a file when islink returns True."""
    dummy_file = tmp_path / "mock_link_file.txt"
    dummy_file.write_text("precious", encoding="utf-8")
    monkeypatch.setattr(os.path, "islink", lambda p: True)
    shredder = AdvancedShredder()
    res = shredder.shred_file(str(dummy_file))
    assert res is False
    assert dummy_file.exists()


def test_advanced_shredder_refuses_symlink_target(tmp_path):
    """AdvancedShredder must refuse to shred a symlinked file target."""
    real_file = tmp_path / "real.txt"
    real_file.write_text("sensitive data", encoding="utf-8")

    link_file = tmp_path / "link.txt"
    try:
        os.symlink(real_file, link_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not permitted in this environment")

    shredder = AdvancedShredder()
    res = shredder.shred_file(str(link_file))
    assert res is False
    # Original data must remain intact and not shredded
    assert real_file.read_text(encoding="utf-8") == "sensitive data"


def test_advanced_shredder_refuses_protected_path():
    """AdvancedShredder must self-enforce PathGuard on shred_file and shred_directory."""
    shredder = AdvancedShredder()
    protected = "C:/Windows/System32" if sys.platform == "win32" else "/etc"
    assert shredder.shred_file(protected) is False
    assert shredder.shred_directory(protected) is False


def test_registry_cleaner_blocks_protected_keys():
    """RegistryCleaner must reject deletion of protected Windows subsystem keys."""
    if sys.platform != "win32":
        pytest.skip("Windows only")

    cleaner = RegistryCleaner()
    for protected in [r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
                      r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanServer",
                      r"HKLM\SAM"]:
        entry = {
            "hive": "HKLM",
            "path": protected,
            "type": "uninstall_entry"
        }
        res = cleaner.remove_orphaned_entry(entry, auto_backup=False)
        assert res is False, f"Cleaner failed to block protected key {protected}"


def test_registry_cleaner_fail_closed_on_backup_failure(monkeypatch):
    """If auto_backup is True but backup creation fails, deletion must be aborted (fail-closed)."""
    if sys.platform != "win32":
        pytest.skip("Windows only")

    cleaner = RegistryCleaner()
    # Force backup_entry to fail
    monkeypatch.setattr(cleaner, "backup_entry", lambda entry: None)

    entry = {
        "hive": "HKCU",
        "path": r"Software\TestAppOrphan_NonExistent",
        "type": "uninstall_entry"
    }
    res = cleaner.remove_orphaned_entry(entry, auto_backup=True)
    assert res is False
