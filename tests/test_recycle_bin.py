"""Unit tests for the Recycle Bin measurer & emptier (system_tools/recycle_bin)."""

from __future__ import annotations

from pathlib import Path

from cortex_unified.system_tools.recycle_bin import RecycleBinManager


def _make_fake_bin(root: Path, files: dict[str, bytes]) -> Path:
    """Create a fake ``$RECYCLE.BIN`` tree under *root* and return it."""
    bin_dir = root / "$RECYCLE.BIN" / "S-1-5-21-fake"
    bin_dir.mkdir(parents=True)
    for name, data in files.items():
        (bin_dir / name).write_bytes(data)
    return root


class TestMeasure:
    """Tests for RecycleBinManager.measure."""

    def test_empty_drive_reports_no_drives(self, tmp_path: Path):
        """A drive root without any bin dir yields no entries."""
        rep = RecycleBinManager().measure(roots=[tmp_path])
        assert rep.total_bytes == 0
        assert rep.total_items == 0
        assert rep.drives == []

    def test_fake_bin_sizes_and_counts(self, tmp_path: Path):
        """Bin contents are summed correctly (bytes + file count)."""
        drive = _make_fake_bin(tmp_path / "C", {"$Ra1b2c": b"x" * 100, "$Ia1b2c": b"y" * 50})
        rep = RecycleBinManager().measure(roots=[drive])
        assert rep.total_bytes == 150
        assert rep.total_items == 2
        assert len(rep.drives) == 1

    def test_broken_symlink_inside_bin_is_skipped(self, tmp_path: Path):
        """Unreadable/linked entries never break measurement."""
        import os

        drive = _make_fake_bin(tmp_path / "D", {"$Rok": b"z" * 10})
        link = drive / "$RECYCLE.BIN" / "S-1-5-21-fake" / "$Rlink"
        try:
            os.symlink(str(tmp_path / "does-not-exist"), link)
        except (OSError, NotImplementedError):
            pass
        rep = RecycleBinManager().measure(roots=[drive])
        assert rep.total_bytes == 10
        assert rep.total_items == 1


class TestEmptyDryRun:
    """Tests for RecycleBinManager.empty (dry-run only — never touches the real bin)."""

    def test_dry_run_reports_without_deleting(self, tmp_path: Path):
        """dry_run=True reports the measurement and deletes nothing on real drives."""
        res = RecycleBinManager().empty(dry_run=True)
        assert res.emptied is False
        assert res.freed_bytes >= 0
        assert "Dry run" in res.message
