"""Unit tests for CleanerService.scan_custom_roots, HubScanWorker, and CleanupHubPage targeted scanning."""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from cortex_unified.engine.service import CleanerService, CleanupReport, CategoryScan
from cortex_unified.engine.categories import CleanupCategory, RiskLevel
from cortex_unified.engine.models import FileEntry
from cortex_unified.ui.premium.cleanup_hub_page import CleanupHubPage, HubScanWorker

pytest.importorskip("PySide6", reason="PySide6 not installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    """Provide shared QApplication for GUI testing."""
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def window(app):
    """Provide a headless PremiumMainWindow fixture."""
    import gc
    from cortex_unified.ui.premium.theme import apply_theme
    from cortex_unified.ui.premium.window import PremiumMainWindow

    if not getattr(app, "_theme_applied", False):
        apply_theme(app, "dark")
        app._theme_applied = True
    win = PremiumMainWindow("dark")
    win.resize(1180, 760)
    yield win
    win._force_quit = True
    win.close()
    win.deleteLater()
    app.processEvents()
    gc.collect()


class TestCustomRootsScan:
    """Tests for CleanerService.scan_custom_roots."""

    def test_empty_directory_returns_zero(self, tmp_path: Path):
        """Scanning an empty folder must return 0 files and 0 bytes."""
        empty_dir = tmp_path / "empty_folder"
        empty_dir.mkdir()

        svc = CleanerService()
        report = svc.scan_custom_roots([empty_dir])

        assert report.total_files == 0
        assert report.total_reclaimable_bytes == 0
        assert len(report.scans) == 0

    def test_single_empty_file(self, tmp_path: Path):
        """Scanning a single empty file (0 bytes) reports 1 file under custom_empty_files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        svc = CleanerService()
        report = svc.scan_custom_roots([empty_file])

        assert report.total_files == 1
        assert report.total_reclaimable_bytes == 0
        assert len(report.scans) == 1
        scan = report.scans[0]
        assert scan.category.id == "custom_empty_files"
        assert len(scan.entries) == 1
        assert scan.entries[0].path == empty_file

    def test_directory_with_cleanable_categories(self, tmp_path: Path):
        """Scanning a directory categorizes build caches, temp files, logs, and empty files."""
        # 1. Build cache (node_modules)
        nm_dir = tmp_path / "node_modules" / "pkg"
        nm_dir.mkdir(parents=True)
        pkg_file = nm_dir / "index.js"
        pkg_file.write_bytes(b"console.log('test');" * 10)  # non-zero

        # 2. Temp file
        tmp_file = tmp_path / "scratch.tmp"
        tmp_file.write_bytes(b"temporary" * 50)

        # 3. Log file
        log_file = tmp_path / "app.log"
        log_file.write_bytes(b"error at 12:00\n" * 20)

        # 4. Cruft file
        cruft_file = tmp_path / "desktop.ini"
        cruft_file.write_bytes(b"[ViewState]")

        # 5. Empty file
        zero_file = tmp_path / "zero.dat"
        zero_file.write_bytes(b"")

        # 6. Important non-junk file (must NOT be counted in cleanup scans)
        important_file = tmp_path / "main.py"
        important_file.write_text("print('hello world')", encoding="utf-8")

        svc = CleanerService()
        report = svc.scan_custom_roots([tmp_path])

        cat_ids = {s.category.id for s in report.scans}
        assert "custom_build_caches" in cat_ids
        assert "custom_temp_files" in cat_ids
        assert "custom_log_files" in cat_ids
        assert "custom_cruft_files" in cat_ids
        assert "custom_empty_files" in cat_ids

        all_paths = {e.path for s in report.scans for e in s.entries}
        assert important_file not in all_paths
        assert pkg_file in all_paths
        assert tmp_file in all_paths
        assert log_file in all_paths
        assert cruft_file in all_paths
        assert zero_file in all_paths

        assert report.total_files == 5
        assert report.total_reclaimable_bytes > 0


class TestHubScanWorkerCustomRoots:
    """Tests for HubScanWorker handling custom_roots."""

    def test_worker_emits_custom_scan_report(self, tmp_path: Path):
        """HubScanWorker with custom_roots runs scan_custom_roots and emits finished."""
        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        worker = HubScanWorker(custom_roots=[empty_dir])
        received_reports = []
        worker.finished.connect(received_reports.append)

        worker.run()

        assert len(received_reports) == 1
        rep = received_reports[0]
        assert rep.total_files == 0
        assert rep.total_reclaimable_bytes == 0


class TestCleanupHubPageCustomRoots:
    """Tests for CleanupHubPage displaying accurate counts for custom targets."""

    def test_empty_target_displays_zero_and_clean_state(self, window, tmp_path: Path):
        """When an empty directory is scanned, summary shows 0 B / 0 files and Clean button is disabled."""
        page = CleanupHubPage(window)
        empty_dir = tmp_path / "empty_test_folder"
        empty_dir.mkdir()

        page._custom_roots = [empty_dir]
        page._update_roots_status()
        assert "Active Scan Target:" in page.target_roots_label.text()
        assert not page.btn_clear_roots.isHidden()

        # Simulate scan result of empty target
        empty_report = CleanupReport(scans=[], duration_seconds=0.01)
        page._on_scanned(empty_report)

        assert page.card_total.value() in ("0.0 B", "0 B")
        assert page.card_files.value() == "0"
        assert page.card_cats.value() == "0"
        assert not page.clean_btn.isEnabled()

    def test_target_with_findings_populates_grid_and_enables_clean(self, window, tmp_path: Path):
        """When custom target has findings, summary shows real counts and Clean button is enabled."""
        page = CleanupHubPage(window)
        target_dir = tmp_path / "target_folder"
        target_dir.mkdir()

        page._custom_roots = [target_dir]
        page._update_roots_status()

        cat = CleanupCategory(
            id="custom_build_caches",
            label="Project Build & Package Caches",
            description="Build caches",
            risk=RiskLevel.LOW,
            paths=(target_dir,),
            reversible=True,
            default_enabled=True,
        )
        entry = FileEntry(path=target_dir / "index.js", size=1024 * 1024, mtime=0.0)
        scan = CategoryScan(category=cat, entries=[entry], total_bytes=1024 * 1024)
        report = CleanupReport(scans=[scan], duration_seconds=0.05)

        page._on_scanned(report)

        assert "1.00 MB" in page.card_total.value() or "1.0 MB" in page.card_total.value()
        assert page.card_files.value() == "1"
        assert page.card_cats.value() == "1"
        assert page.clean_btn.isEnabled()
        assert page.grid.count() == 1

    def test_reset_roots_restores_default_state(self, window, tmp_path: Path):
        """_clear_custom_roots resets targets back to default system partitions."""
        page = CleanupHubPage(window)
        page._custom_roots = [tmp_path]
        page._update_roots_status()
        assert not page.btn_clear_roots.isHidden()

        page._custom_roots.clear()
        page._update_roots_status()
        assert "Active Scan Roots: Full Device" in page.target_roots_label.text()
        assert page.btn_clear_roots.isHidden()

    def test_cleanup_hub_initial_state_no_autoscan(self, window):
        """CleanupHubPage opens in ready state without auto-scanning."""
        page = CleanupHubPage(window)
        assert page._autoload is None
        assert page.scan_btn.isEnabled()
        assert "Start Scan" in page.scan_btn.text()
        assert not page.clean_btn.isEnabled()
        assert not page.clean_all_btn.isEnabled()
        assert page.state.mode() == "empty"

    def test_cleanup_hub_target_selection_controls(self, window):
        """Target scope buttons switch between full device and system drive."""
        page = CleanupHubPage(window)
        assert page._custom_roots == []

        page._select_target_system_drive()
        assert len(page._custom_roots) == 1
        assert "Active Scan Target:" in page.target_roots_label.text()
        assert not page.btn_clear_roots.isHidden()

        page._select_target_full_device()
        assert page._custom_roots == []
        assert "Active Scan Roots: Full Device" in page.target_roots_label.text()
        assert page.btn_clear_roots.isHidden()

    def test_cleanup_hub_live_activity_logging(self, window):
        """Live activity feed logs scanning events dynamically."""
        page = CleanupHubPage(window)
        page._log_feed("Testing live feed item 1")
        page._on_progress("Testing live progress item 2")

        log_content = page.scan_log_text.toPlainText()
        assert "Testing live feed item 1" in log_content
        assert "Testing live progress item 2" in log_content
        assert page.scan_status.text() == "Testing live progress item 2"

    def test_cleanup_hub_itemized_table_and_dialog(self, window, tmp_path: Path):
        """Itemized table view and CategoryFilesDialog accurately display discovered files."""
        from cortex_unified.ui.premium.cleanup_hub_page import CategoryFilesDialog

        page = CleanupHubPage(window)
        target_dir = tmp_path / "mock_app"
        target_dir.mkdir()
        file1 = target_dir / "cache1.tmp"
        file1.write_bytes(b"data" * 100)
        file2 = target_dir / "cache2.tmp"
        file2.write_bytes(b"data" * 200)

        cat = CleanupCategory(
            id="custom_temp_files",
            label="Temporary & Backup Files",
            description="Temp files",
            risk=RiskLevel.LOW,
            paths=(target_dir,),
            reversible=True,
            default_enabled=True,
        )
        entries = [
            FileEntry(path=file1, size=400, mtime=1700000000.0),
            FileEntry(path=file2, size=800, mtime=1700000001.0),
        ]
        scan = CategoryScan(category=cat, entries=entries, total_bytes=1200)
        report = CleanupReport(scans=[scan], duration_seconds=0.02)

        page._on_scanned(report)

        # Verify all-files breakdown table
        assert page.all_files_table.rowCount() == 2
        page._switch_to_table_view()
        assert page.view_stack.currentIndex() == 1
        page._switch_to_cards_view()
        assert page.view_stack.currentIndex() == 0

        # Filter all-files table
        page._filter_all_files_table("cache1")
        assert page.all_files_table.rowCount() == 1
        page._filter_all_files_table("")
        assert page.all_files_table.rowCount() == 2

        # Verify CategoryFilesDialog
        dlg = CategoryFilesDialog(page, scan, cat)
        assert dlg.table.rowCount() == 2
        dlg._apply_filter("cache2")
        assert len(dlg._filtered) == 1
        assert dlg.table.rowCount() == 1
        dlg.close()
